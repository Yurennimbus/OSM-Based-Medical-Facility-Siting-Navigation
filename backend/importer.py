import os
import json
import shutil
import geopandas as gpd
import pandas as pd
from .config import (
    DATA_DIR, MANDATORY_LAYERS, BASE_DIR,
    CAPACITY_SCORE_DEFAULT, SUPPORTED_EXTENSIONS,
    get_city_config, get_all_city_configs, resolve_data_path,
)
from .database import register_city, upsert_facility_capacity


def _read_spatial_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".shp":
        return gpd.read_file(filepath, encoding="utf-8")
    elif ext in (".geojson", ".json"):
        return gpd.read_file(filepath)
    elif ext == ".gpkg":
        return gpd.read_file(filepath)
    elif ext == ".csv":
        df = pd.read_csv(filepath, encoding="utf-8")
        return _df_to_gdf(df, filepath)
    else:
        try:
            return gpd.read_file(filepath)
        except Exception:
            raise ValueError(f"Unsupported file format: {ext}")


def _df_to_gdf(df, filepath_hint=""):
    lon_candidates = ["wgs_lng", "longitude", "lon", "lng", "经度", "x", "X"]
    lat_candidates = ["wgs_lat", "latitude", "lat", "纬度", "y", "Y"]
    geom_candidates = ["geometry", "geom", "wkt", "WKT"]
    lon_col = _detect_field(df, lon_candidates)
    lat_col = _detect_field(df, lat_candidates)
    geom_col = _detect_field(df, geom_candidates)
    if geom_col:
        from shapely import wkt as shapely_wkt
        df[geom_col] = df[geom_col].apply(lambda v: shapely_wkt.loads(v) if isinstance(v, str) else v)
        return gpd.GeoDataFrame(df, geometry=geom_col, crs="EPSG:4326")
    if lon_col and lat_col:
        from shapely.geometry import Point
        geom = [Point(x, y) for x, y in zip(df[lon_col], df[lat_col])]
        return gpd.GeoDataFrame(df, geometry=geom, crs="EPSG:4326")
    raise ValueError(f"Cannot infer geometry from file: {filepath_hint}")


def detect_layers(data_path):
    layers = {}
    if not os.path.isdir(data_path):
        return layers
    for fname in sorted(os.listdir(data_path)):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            if ext == ".csv":
                pass
            else:
                continue
        fpath = os.path.join(data_path, fname)
        try:
            gdf = _read_spatial_file(fpath)
            if fname.lower().endswith(".shp"):
                layer_name = os.path.splitext(fname)[0].lower()
            else:
                layer_name = os.path.splitext(fname)[0].lower()
            if "人口" in fname:
                layer_name = "population"
            elif "街道" in fname and "人口" in fname:
                layer_name = "population"
            layers[layer_name] = {
                "file": fname,
                "feature_count": len(gdf),
                "geometry_type": gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else "Unknown",
                "fields": list(gdf.columns),
            }
        except Exception as e:
            print(f"  [WARN] Could not read {fname}: {e}")
    return layers


def _detect_field(gdf, candidates):
    if hasattr(gdf, "columns"):
        cols_lower = {str(c).lower(): c for c in gdf.columns}
    else:
        return None
    for candidate in candidates:
        key = candidate.lower()
        if key in cols_lower:
            return cols_lower[key]
    return None


def import_city_from_config(schema_name):
    city_cfg = get_city_config(schema_name)
    if not city_cfg:
        raise ValueError(f"City '{schema_name}' not found in config.yaml")
    city_name = city_cfg.get("name", schema_name)
    source_dir = resolve_data_path(city_cfg)
    if not source_dir or not os.path.isdir(source_dir):
        raise ValueError(f"Source directory not found for '{schema_name}'. Check 'source' in config.yaml.")
    target_path = os.path.join(DATA_DIR, schema_name)
    os.makedirs(target_path, exist_ok=True)
    layer_configs = city_cfg.get("layers", {})
    imported_layers = {}
    for layer_name, lcfg in layer_configs.items():
        fname = lcfg.get("file", "")
        if not fname:
            continue
        src_file = os.path.join(source_dir, fname)
        dst_file = os.path.join(target_path, fname)
        if not os.path.exists(src_file):
            print(f"  [SKIP] {layer_name}: source file not found: {src_file}")
            continue
        if not os.path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
            shutil.copy2(src_file, dst_file)
        try:
            gdf = _read_spatial_file(dst_file)
            imported_layers[layer_name] = {
                "file": fname,
                "feature_count": len(gdf),
                "geometry_type": gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else "Unknown",
                "fields": list(gdf.columns),
            }
        except Exception as e:
            print(f"  [WARN] Could not load {layer_name}: {e}")
    mandatory_found = [l for l in MANDATORY_LAYERS if l in imported_layers]
    if len(mandatory_found) < len(MANDATORY_LAYERS):
        missing = set(MANDATORY_LAYERS) - set(imported_layers.keys())
        raise ValueError(f"Missing mandatory layers: {missing}")
    capacity_imported = _import_capacity_from_health(schema_name, target_path, layer_configs)
    bounds = city_cfg.get("bounds") or _compute_bounds(target_path, imported_layers)
    register_city(
        name=city_name,
        schema_name=schema_name,
        data_path=target_path,
        bounds=bounds,
        available_layers=list(imported_layers.keys()),
    )
    return {
        "city_name": city_name,
        "schema_name": schema_name,
        "layers": {k: {"feature_count": v["feature_count"], "geometry_type": v["geometry_type"]} for k, v in imported_layers.items()},
        "bounds": bounds,
        "capacity_imported": capacity_imported,
    }


def _import_capacity_from_health(schema_name, target_path, layer_configs):
    health_cfg = layer_configs.get("health", {})
    health_file = health_cfg.get("file")
    if not health_file:
        return 0
    health_path = os.path.join(target_path, health_file)
    if not os.path.exists(health_path):
        return 0
    gdf = _read_spatial_file(health_path)
    name_field = _detect_field(gdf, ["name", "facility_name", "名称"])
    cat_field = _detect_field(gdf, ["category", "fclass", "type", "facility_type", "类型"])
    lon_field = _detect_field(gdf, ["wgs_lng", "longitude", "lon", "lng", "经度"])
    lat_field = _detect_field(gdf, ["wgs_lat", "latitude", "lat", "纬度"])
    attr_field = _detect_field(gdf, ["attribute", "capacity", "能力"])
    count = 0
    for _, row in gdf.iterrows():
        try:
            lon = float(row[lon_field]) if lon_field else float(row.geometry.x)
            lat = float(row[lat_field]) if lat_field else float(row.geometry.y)
        except Exception:
            continue
        name = str(row[name_field]) if name_field else f"Facility_{count}"
        category = str(row[cat_field]) if cat_field else "unknown"
        score = CAPACITY_SCORE_DEFAULT
        if attr_field:
            try:
                score = float(row[attr_field])
            except (ValueError, TypeError):
                pass
        if name_field and "建设中" in str(row[name_field]):
            score = 0.0
        upsert_facility_capacity(schema_name, name, lon, lat, score, category)
        count += 1
    return count


def _compute_bounds(data_path, layers_info):
    all_gdfs = []
    for layer_name, info in layers_info.items():
        try:
            gdf = _read_spatial_file(os.path.join(data_path, info["file"]))
            all_gdfs.append(gdf)
        except Exception:
            pass
    if not all_gdfs:
        return None
    combined = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=all_gdfs[0].crs)
    tb = combined.total_bounds
    return {"min_lon": float(tb[0]), "min_lat": float(tb[1]), "max_lon": float(tb[2]), "max_lat": float(tb[3])}


def import_all_configured_cities():
    results = []
    for schema_name in get_all_city_configs():
        try:
            r = import_city_from_config(schema_name)
            results.append(r)
        except Exception as e:
            print(f"Warning: Failed to import {schema_name}: {e}")
    return results


def load_layer(data_path, layer_name):
    if not os.path.isdir(data_path):
        return None
    name_lower = layer_name.lower()
    if name_lower == "boundary":
        return load_boundary_layer(data_path)
    for fname in sorted(os.listdir(data_path)):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            if ext == ".csv":
                pass
            else:
                continue
        base = os.path.splitext(fname)[0].lower()
        if base == name_lower:
            return _read_spatial_file(os.path.join(data_path, fname))
        if name_lower == "population" and "人口" in fname:
            return _read_spatial_file(os.path.join(data_path, fname))
        if name_lower == "railway_stations" and "station" in base:
            return _read_spatial_file(os.path.join(data_path, fname))
        if name_lower == "railways" and ("railway" in base or "铁路" in fname):
            return _read_spatial_file(os.path.join(data_path, fname))
    return None


def load_boundary_layer(data_path):
    if not os.path.isdir(data_path):
        return None
    best_gdf = None
    best_count = float("inf")
    for fname in sorted(os.listdir(data_path)):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        try:
            gdf = _read_spatial_file(os.path.join(data_path, fname))
            if len(gdf) == 0:
                continue
            geom_type = gdf.geometry.geom_type.iloc[0]
            if "Polygon" in geom_type and len(gdf) < best_count:
                best_gdf = gdf
                best_count = len(gdf)
        except Exception:
            continue
    return best_gdf


def import_city_from_path(city_name, schema_name, source_path):
    if not os.path.isdir(source_path):
        raise ValueError(f"Directory not found: {source_path}")
    raw_layers = detect_layers(source_path)
    mandatory_found = [l for l in MANDATORY_LAYERS if l in raw_layers]
    if len(mandatory_found) < len(MANDATORY_LAYERS):
        missing = set(MANDATORY_LAYERS) - set(raw_layers.keys())
        raise ValueError(f"Missing mandatory layers: {missing}")
    target_path = os.path.join(DATA_DIR, schema_name)
    os.makedirs(target_path, exist_ok=True)
    for layer_name, info in raw_layers.items():
        src_file = os.path.join(source_path, info["file"])
        dst_file = os.path.join(target_path, info["file"])
        if not os.path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
            shutil.copy2(src_file, dst_file)
    capacity_imported = 0
    if "health" in raw_layers:
        health_path = os.path.join(target_path, raw_layers["health"]["file"])
        gdf = _read_spatial_file(health_path)
        name_field = _detect_field(gdf, ["name", "facility_name", "名称"])
        cat_field = _detect_field(gdf, ["category", "fclass", "type", "facility_type", "类型"])
        lon_field = _detect_field(gdf, ["wgs_lng", "longitude", "lon", "lng", "经度"])
        lat_field = _detect_field(gdf, ["wgs_lat", "latitude", "lat", "纬度"])
        attr_field = _detect_field(gdf, ["attribute", "capacity", "能力"])
        for _, row in gdf.iterrows():
            try:
                lon = float(row[lon_field]) if lon_field else float(row.geometry.x)
                lat = float(row[lat_field]) if lat_field else float(row.geometry.y)
            except Exception:
                continue
            name = str(row[name_field]) if name_field else f"Facility_{capacity_imported}"
            category = str(row[cat_field]) if cat_field else "unknown"
            score = CAPACITY_SCORE_DEFAULT
            if attr_field:
                try:
                    score = float(row[attr_field])
                except (ValueError, TypeError):
                    pass
            if name_field and "建设中" in str(row[name_field]):
                score = 0.0
            upsert_facility_capacity(schema_name, name, lon, lat, score, category)
            capacity_imported += 1
    bounds = _compute_bounds(target_path, raw_layers)
    register_city(
        name=city_name,
        schema_name=schema_name,
        data_path=target_path,
        bounds=bounds,
        available_layers=list(raw_layers.keys()),
    )
    return {
        "city_name": city_name,
        "schema_name": schema_name,
        "layers": {k: {"feature_count": v["feature_count"], "geometry_type": v["geometry_type"]} for k, v in raw_layers.items()},
        "bounds": bounds,
        "capacity_imported": capacity_imported,
    }
