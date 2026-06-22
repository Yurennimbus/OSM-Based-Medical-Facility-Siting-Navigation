import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from scipy.spatial import cKDTree
from .config import GRID_CELL_SIZE, GRID_MAX_CELLS
from .importer import load_layer, load_boundary_layer
from .database import get_facility_capacities


def _create_grid(bounds, cell_size, boundary_gdf=None):
    minx, miny, maxx, maxy = bounds
    cols = int(np.ceil((maxx - minx) / cell_size))
    rows = int(np.ceil((maxy - miny) / cell_size))
    if cols * rows > GRID_MAX_CELLS:
        cell_size = max(cell_size, max(maxx - minx, maxy - miny) / 200)
        cols = int(np.ceil((maxx - minx) / cell_size))
        rows = int(np.ceil((maxy - miny) / cell_size))
    cells = []
    for r in range(rows):
        y = miny + r * cell_size
        for c in range(cols):
            x = minx + c * cell_size
            poly = box(x, y, x + cell_size, y + cell_size)
            cells.append({
                "geometry": poly,
                "row": r,
                "col": c,
                "centroid": poly.centroid,
            })
    grid_gdf = gpd.GeoDataFrame(cells, crs="EPSG:4326")
    if boundary_gdf is not None and len(boundary_gdf) > 0:
        try:
            boundary_union = boundary_gdf.geometry.unary_union
            grid_gdf["_in_bound"] = grid_gdf["centroid"].apply(lambda p: p.within(boundary_union))
            grid_gdf = grid_gdf[grid_gdf["_in_bound"]].drop(columns=["_in_bound"]).reset_index(drop=True)
        except Exception:
            pass
    if len(grid_gdf) == 0:
        grid_gdf, _ = _create_grid(bounds, cell_size, None)
    return grid_gdf, cell_size


def _normalize(series):
    mn, mx = series.min(), series.max()
    if mx - mn < 1e-10:
        return pd.Series(0.5, index=series.index)
    return (series - mn) / (mx - mn)


def _compute_population_score(grid_gdf, pop_gdf):
    if pop_gdf is None or len(pop_gdf) == 0:
        return pd.Series(0.5, index=grid_gdf.index)
    pop_field = None
    for col in pop_gdf.columns:
        col_lower = str(col).lower()
        if "总人口" in col or "total" in col_lower or "合计" in col:
            pop_field = col
            break
    if pop_field is None:
        for c in ["population", "total_pop", "pop"]:
            if c in pop_gdf.columns:
                pop_field = c
                break
    centroids = np.array([[c.x, c.y] for c in grid_gdf["centroid"]])
    pop_points = np.array([[p.x, p.y] for p in pop_gdf.geometry])
    pop_values = pop_gdf[pop_field].fillna(0).values if pop_field else np.ones(len(pop_gdf))
    tree = cKDTree(pop_points)
    scores = np.zeros(len(grid_gdf))
    for i, center in enumerate(centroids):
        dists, idxs = tree.query(center, k=min(5, len(pop_points)))
        if not isinstance(dists, np.ndarray):
            dists = np.array([dists])
            idxs = np.array([idxs])
        dists_m = dists * 111000
        weights = 1.0 / (dists_m + 100)
        scores[i] = np.sum(pop_values[idxs] * weights)
    return _normalize(pd.Series(scores))


def _compute_traffic_score(grid_gdf, roads_gdf, railway_stations_gdf=None):
    if roads_gdf is None or len(roads_gdf) == 0:
        base_score = pd.Series(0.5, index=grid_gdf.index)
    else:
        speed_weight_map = {
            "motorway": 5, "motorway_link": 4, "trunk": 4, "trunk_link": 3,
            "primary": 3, "primary_link": 2.5, "secondary": 2, "secondary_link": 1.5,
            "tertiary": 1.5, "unclassified": 1, "residential": 0.8, "service": 0.5,
            "track": 0.3, "pedestrian": 0.2, "path": 0.1,
        }
        rgdf = roads_gdf.copy()
        if "fclass" in rgdf.columns:
            rgdf["speed_weight"] = rgdf["fclass"].map(speed_weight_map).fillna(1.0)
        else:
            rgdf["speed_weight"] = 1.0
        road_geoms = rgdf.geometry.values
        road_weights = rgdf["speed_weight"].values
        midpoints = []
        mid_weights = []
        for j, geom in enumerate(road_geoms):
            try:
                if geom.geom_type == "MultiLineString":
                    for line in geom.geoms:
                        midpoints.append([line.interpolate(0.5, normalized=True).x, line.interpolate(0.5, normalized=True).y])
                        mid_weights.append(road_weights[j])
                elif geom.geom_type == "LineString":
                    midpoints.append([geom.interpolate(0.5, normalized=True).x, geom.interpolate(0.5, normalized=True).y])
                    mid_weights.append(road_weights[j])
            except Exception:
                pass
        if midpoints:
            midpoints = np.array(midpoints)
            mid_weights = np.array(mid_weights)
            tree = cKDTree(midpoints)
            centroids = np.array([[c.x, c.y] for c in grid_gdf["centroid"]])
            scores = np.zeros(len(grid_gdf))
            for i, center in enumerate(centroids):
                dists, idxs = tree.query(center, k=min(3, len(midpoints)))
                if not isinstance(dists, np.ndarray):
                    dists = np.array([dists])
                    idxs = np.array([idxs])
                dists_m = dists * 111000
                rw = mid_weights[idxs]
                scores[i] = np.sum(rw / (dists_m + 50))
            base_score = _normalize(pd.Series(scores))
        else:
            base_score = pd.Series(0.5, index=grid_gdf.index)

    if railway_stations_gdf is not None and len(railway_stations_gdf) > 0:
        st_points = np.array([[p.x, p.y] for p in railway_stations_gdf.geometry])
        st_tree = cKDTree(st_points)
        centroids = np.array([[c.x, c.y] for c in grid_gdf["centroid"]])
        station_bonus = np.zeros(len(grid_gdf))
        for i, center in enumerate(centroids):
            dists, _ = st_tree.query(center, k=min(3, len(st_points)))
            if not isinstance(dists, np.ndarray):
                dists = np.array([dists])
            dists_m = dists * 111000
            bonus = np.sum(1.0 / (dists_m + 300))
            station_bonus[i] = min(bonus, 5.0) / 5.0
        station_score = _normalize(pd.Series(station_bonus))
        combined = 0.7 * base_score + 0.3 * station_score
        return _normalize(combined)
    return base_score


def _compute_competition_score(grid_gdf, health_gdf, facility_type, capacity_map):
    if health_gdf is None or len(health_gdf) == 0:
        return pd.Series(0.5, index=grid_gdf.index)
    cat_field = None
    for col in health_gdf.columns:
        if str(col).lower() in ["category", "fclass", "type", "facility_type"]:
            cat_field = col
            break
    if cat_field and facility_type:
        competitors = health_gdf[health_gdf[cat_field] == facility_type]
    else:
        competitors = health_gdf
    if len(competitors) == 0:
        return pd.Series(0.8, index=grid_gdf.index)
    comp_points = np.array([[p.x, p.y] for p in competitors.geometry])
    centroids = np.array([[c.x, c.y] for c in grid_gdf["centroid"]])
    tree = cKDTree(comp_points)
    scores = np.zeros(len(grid_gdf))
    for i, center in enumerate(centroids):
        dists, _ = tree.query(center, k=min(3, len(comp_points)))
        if not isinstance(dists, np.ndarray):
            dists = np.array([dists])
        min_d = np.min(dists) * 111000
        if min_d < 200:
            scores[i] = 0.1
        elif min_d > 5000:
            scores[i] = 1.0
        else:
            scores[i] = (min_d - 200) / 4800
    return _normalize(pd.Series(scores))


def _compute_landuse_score(grid_gdf, landuse_gdf):
    if landuse_gdf is None or len(landuse_gdf) == 0:
        return pd.Series(0.5, index=grid_gdf.index)
    fclass_field = None
    for col in landuse_gdf.columns:
        if str(col).lower() in ["fclass", "landuse", "type", "class"]:
            fclass_field = col
            break
    if fclass_field:
        residential = landuse_gdf[landuse_gdf[fclass_field] == "residential"]
    else:
        residential = landuse_gdf
    if len(residential) == 0:
        return pd.Series(0.3, index=grid_gdf.index)
    try:
        residential_union = unary_union(residential.geometry.values)
    except Exception:
        residential_union = residential.geometry.unary_union
    scores = np.zeros(len(grid_gdf))
    for i, row in grid_gdf.iterrows():
        cell_center = row["centroid"]
        dist = cell_center.distance(residential_union) * 111000
        if dist < 100:
            scores[i] = 1.0
        elif dist > 3000:
            scores[i] = 0.1
        else:
            scores[i] = 1.0 - (dist - 100) / 2900
    return _normalize(pd.Series(scores))


def compute_suitability(data_path, w_population, w_traffic, w_competition, w_landuse, facility_type, city_schema, grid_size=None):
    if grid_size is None:
        grid_size = GRID_CELL_SIZE
    health_gdf = load_layer(data_path, "health")
    landuse_gdf = load_layer(data_path, "landuse")
    roads_gdf = load_layer(data_path, "roads")
    if health_gdf is None or landuse_gdf is None or roads_gdf is None:
        raise ValueError("Missing mandatory layers (health, landuse, roads)")
    pop_gdf = load_layer(data_path, "population")
    railway_stations_gdf = load_layer(data_path, "railway_stations")
    boundary_gdf = load_boundary_layer(data_path)
    combined = gpd.GeoDataFrame(pd.concat([health_gdf, landuse_gdf, roads_gdf], ignore_index=True), crs=health_gdf.crs)
    bounds = combined.total_bounds
    grid_gdf, actual_grid_size = _create_grid(bounds, grid_size, boundary_gdf)
    capacity_map = get_facility_capacities(city_schema)
    grid_gdf["score_population"] = _compute_population_score(grid_gdf, pop_gdf)
    grid_gdf["score_traffic"] = _compute_traffic_score(grid_gdf, roads_gdf, railway_stations_gdf)
    grid_gdf["score_competition"] = _compute_competition_score(grid_gdf, health_gdf, facility_type, capacity_map)
    grid_gdf["score_landuse"] = _compute_landuse_score(grid_gdf, landuse_gdf)
    grid_gdf["suitability"] = (
        w_population * grid_gdf["score_population"]
        + w_traffic * grid_gdf["score_traffic"]
        + w_competition * grid_gdf["score_competition"]
        + w_landuse * grid_gdf["score_landuse"]
    )
    top5 = grid_gdf.nlargest(5, "suitability")
    top5_list = []
    for _, row in top5.iterrows():
        top5_list.append({
            "row": int(row["row"]),
            "col": int(row["col"]),
            "centroid": [float(row["centroid"].x), float(row["centroid"].y)],
            "suitability": float(row["suitability"]),
            "score_population": float(row["score_population"]),
            "score_traffic": float(row["score_traffic"]),
            "score_competition": float(row["score_competition"]),
            "score_landuse": float(row["score_landuse"]),
        })
    grid_gdf["centroid_lon"] = grid_gdf["centroid"].apply(lambda p: p.x)
    grid_gdf["centroid_lat"] = grid_gdf["centroid"].apply(lambda p: p.y)
    grid_for_json = grid_gdf[["geometry", "suitability", "score_population", "score_traffic", "score_competition", "score_landuse", "row", "col"]]
    import json
    grid_geojson = json.loads(grid_for_json.to_json())
    return {
        "grid_geojson": grid_geojson,
        "top5_grids": top5_list,
        "parameters": {
            "w_population": w_population,
            "w_traffic": w_traffic,
            "w_competition": w_competition,
            "w_landuse": w_landuse,
            "facility_type": facility_type,
            "grid_size": actual_grid_size,
            "grid_cells": len(grid_gdf),
        },
    }
