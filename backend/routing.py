import numpy as np
import networkx as nx
from shapely.geometry import Point
from scipy.spatial import cKDTree
import pyproj
from .config import ROAD_SPEED_MAP, ROUTING_SNAP_TOLERANCE_M, ROUTING_MAX_CANDIDATES, ROUTING_PADDING_DEG
from .importer import load_layer
from .database import get_facility_capacities

_transformer_to_m = None


def _get_transformer():
    global _transformer_to_m
    if _transformer_to_m is None:
        _transformer_to_m = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    return _transformer_to_m


def _lonlat_to_meters(lon, lat):
    t = _get_transformer()
    return t.transform(lon, lat)


def _extract_road_segments(roads_gdf, max_segments=30000):
    segments = []
    for _, row in roads_gdf.iterrows():
        geom = row.geometry
        fclass = row.get("fclass", "unknown")
        if geom is None or geom.is_empty:
            continue
        speed = ROAD_SPEED_MAP.get(fclass, 30)
        try:
            if geom.geom_type == "MultiLineString":
                lines = list(geom.geoms)
            elif geom.geom_type == "LineString":
                lines = [geom]
            else:
                continue
        except Exception:
            continue
        for line in lines:
            if line.length > 1e-8:
                segments.append({
                    "coords": list(line.coords),
                    "speed": speed,
                    "fclass": fclass,
                })
                if len(segments) >= max_segments:
                    return segments
        if len(segments) >= max_segments:
            return segments
    return segments


def _build_graph_with_snapping(segments, points_to_snap):
    G = nx.Graph()
    node_set = {}
    for seg in segments:
        coords = seg["coords"]
        speed = seg["speed"]
        for i in range(len(coords) - 1):
            u_raw = (coords[i][0], coords[i][1])
            v_raw = (coords[i + 1][0], coords[i + 1][1])
            u_key = (round(u_raw[0], 7), round(u_raw[1], 7))
            v_key = (round(v_raw[0], 7), round(v_raw[1], 7))
            if u_key == v_key:
                continue
            ux, uy = _lonlat_to_meters(u_key[0], u_key[1])
            vx, vy = _lonlat_to_meters(v_key[0], v_key[1])
            dist_m = np.sqrt((vx - ux) ** 2 + (vy - uy) ** 2)
            time_cost = dist_m / (speed * 1000 / 3600) if speed > 0 else dist_m / (30 * 1000 / 3600)
            G.add_edge(u_key, v_key, weight=time_cost, distance_km=dist_m / 1000, speed=speed)
            node_set[u_key] = u_raw
            node_set[v_key] = v_raw
    snap_results = {}
    if len(node_set) == 0:
        return G, snap_results
    nodes_arr = np.array(list(node_set.keys()))
    tree = cKDTree(nodes_arr)
    for label, (lon, lat) in points_to_snap:
        mx, my = _lonlat_to_meters(lon, lat)
        dists, idxs = tree.query([lon, lat], k=min(5, len(nodes_arr)))
        if not isinstance(dists, np.ndarray):
            dists = np.array([dists])
            idxs = np.array([idxs])
        nearest_node_key = None
        nearest_dist_m = float("inf")
        for d_deg, idx in zip(dists, idxs):
            n_key = tuple(nodes_arr[idx])
            nx_m, ny_m = _lonlat_to_meters(n_key[0], n_key[1])
            d_m = np.sqrt((mx - nx_m) ** 2 + (my - ny_m) ** 2)
            if d_m < nearest_dist_m:
                nearest_dist_m = d_m
                nearest_node_key = n_key
        if nearest_node_key and nearest_dist_m < ROUTING_SNAP_TOLERANCE_M:
            G.add_node((lon, lat))
            G.add_edge((lon, lat), nearest_node_key, weight=nearest_dist_m / (30 * 1000 / 3600),
                       distance_km=nearest_dist_m / 1000, speed=30)
            snap_results[label] = (lon, lat)
        else:
            snap_results[label] = nearest_node_key
    return G, snap_results


def compute_routes(data_path, start_lon, start_lat, facility_type, alpha, city_schema, max_results=3):
    roads_gdf = load_layer(data_path, "roads")
    if roads_gdf is None or len(roads_gdf) == 0:
        raise ValueError("Roads layer is required for routing")
    health_gdf = load_layer(data_path, "health")
    if health_gdf is None or len(health_gdf) == 0:
        raise ValueError("Health layer is required for routing")
    cat_field = None
    for col in health_gdf.columns:
        if str(col).lower() in ["category", "fclass", "type", "facility_type"]:
            cat_field = col
            break
    if cat_field and facility_type:
        matching = health_gdf[health_gdf[cat_field] == facility_type].copy()
    elif cat_field:
        matching = health_gdf[health_gdf[cat_field].isin(["hospital", "clinic", "pharmacy"])].copy()
    else:
        matching = health_gdf.copy()
    if len(matching) == 0:
        raise ValueError(f"No facilities found for type: {facility_type}")
    capacity_map = get_facility_capacities(city_schema)
    name_field = None
    for col in health_gdf.columns:
        if str(col).lower() in ["name", "facility_name"]:
            name_field = col
            break
    target_points = np.array([[p.x, p.y] for p in matching.geometry])
    tree_t = cKDTree(target_points)
    k_nearest = min(ROUTING_MAX_CANDIDATES, len(target_points))
    dists, idxs = tree_t.query([start_lon, start_lat], k=k_nearest)
    if not isinstance(dists, np.ndarray):
        dists = np.array([dists])
        idxs = np.array([idxs])
    candidates = []
    for dist_deg, idx in zip(dists, idxs):
        row = matching.iloc[idx]
        lon = float(row.geometry.x)
        lat = float(row.geometry.y)
        key = (round(lon, 6), round(lat, 6))
        cap = capacity_map.get(key, 1.0)
        name = str(row[name_field]) if name_field else "Facility"
        candidates.append({
            "lon": lon, "lat": lat, "name": name,
            "capacity_score": cap, "direct_dist_km": dist_deg * 111,
        })
    all_lons = [start_lon] + [c["lon"] for c in candidates]
    all_lats = [start_lat] + [c["lat"] for c in candidates]
    pad = ROUTING_PADDING_DEG
    bb_minx = min(all_lons) - pad
    bb_maxx = max(all_lons) + pad
    bb_miny = min(all_lats) - pad
    bb_maxy = max(all_lats) + pad
    bounds = roads_gdf.geometry.bounds
    cx = (bounds["minx"] + bounds["maxx"]) / 2
    cy = (bounds["miny"] + bounds["maxy"]) / 2
    clip_mask = (
        (cx >= bb_minx) & (cx <= bb_maxx) &
        (cy >= bb_miny) & (cy <= bb_maxy)
    )
    local_roads = roads_gdf[clip_mask]
    if len(local_roads) < 50:
        pad = 0.1
        bb_minx2 = min(all_lons) - pad
        bb_maxx2 = max(all_lons) + pad
        bb_miny2 = min(all_lats) - pad
        bb_maxy2 = max(all_lats) + pad
        clip_mask = (
            (cx >= bb_minx2) & (cx <= bb_maxx2) &
            (cy >= bb_miny2) & (cy <= bb_maxy2)
        )
        local_roads = roads_gdf[clip_mask]
    if len(local_roads) < 20:
        local_roads = roads_gdf
    segments = _extract_road_segments(local_roads)
    points_to_snap = [("start", (start_lon, start_lat))]
    for i, c in enumerate(candidates):
        points_to_snap.append((f"fac_{i}", (c["lon"], c["lat"])))
    G, snap_results = _build_graph_with_snapping(segments, points_to_snap)
    start_node = snap_results.get("start")
    results = []
    for i, fac in enumerate(candidates):
        fac_node = snap_results.get(f"fac_{i}")
        if start_node is None or fac_node is None:
            direct_dist = fac["direct_dist_km"]
            composite = direct_dist - alpha * fac["capacity_score"]
            results.append(_make_result(fac, direct_dist, composite, start_lon, start_lat))
            continue
        try:
            if start_node == fac_node:
                total_dist = 0.0
                path_coords = [[start_lon, start_lat]]
            else:
                path = nx.astar_path(G, start_node, fac_node, weight="weight")
                total_dist = 0
                path_coords = []
                for j in range(len(path) - 1):
                    edge_data = G.get_edge_data(path[j], path[j + 1])
                    total_dist += edge_data.get("distance_km", 0)
                    if len(path_coords) == 0:
                        path_coords.append(list(path[j]))
                    path_coords.append(list(path[j + 1]))
            composite = total_dist - alpha * fac["capacity_score"]
            results.append(_make_result(fac, total_dist, composite, start_lon, start_lat, path_coords))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            direct_dist = fac["direct_dist_km"]
            composite = direct_dist - alpha * fac["capacity_score"]
            results.append(_make_result(fac, direct_dist, composite, start_lon, start_lat))
    results.sort(key=lambda x: x["composite_score"])
    return results[:max_results]


def compute_route_to_facility(data_path, start_lon, start_lat, target_lon, target_lat, alpha, city_schema, facility_name="Target"):
    roads_gdf = load_layer(data_path, "roads")
    if roads_gdf is None or len(roads_gdf) == 0:
        raise ValueError("Roads layer is required for routing")
    capacity_map = get_facility_capacities(city_schema)
    key = (round(target_lon, 6), round(target_lat, 6))
    cap = capacity_map.get(key, 1.0)
    pad = ROUTING_PADDING_DEG
    all_lons = [start_lon, target_lon]
    all_lats = [start_lat, target_lat]
    bb_minx = min(all_lons) - pad
    bb_maxx = max(all_lons) + pad
    bb_miny = min(all_lats) - pad
    bb_maxy = max(all_lats) + pad
    bounds = roads_gdf.geometry.bounds
    cx = (bounds["minx"] + bounds["maxx"]) / 2
    cy = (bounds["miny"] + bounds["maxy"]) / 2
    clip_mask = (
        (cx >= bb_minx) & (cx <= bb_maxx) &
        (cy >= bb_miny) & (cy <= bb_maxy)
    )
    local_roads = roads_gdf[clip_mask]
    if len(local_roads) < 50:
        pad = 0.1
        bb_minx2 = min(all_lons) - pad
        bb_maxx2 = max(all_lons) + pad
        bb_miny2 = min(all_lats) - pad
        bb_maxy2 = max(all_lats) + pad
        clip_mask = (
            (cx >= bb_minx2) & (cx <= bb_maxx2) &
            (cy >= bb_miny2) & (cy <= bb_maxy2)
        )
        local_roads = roads_gdf[clip_mask]
    if len(local_roads) < 20:
        local_roads = roads_gdf
    segments = _extract_road_segments(local_roads)
    points_to_snap = [
        ("start", (start_lon, start_lat)),
        ("target", (target_lon, target_lat)),
    ]
    G, snap_results = _build_graph_with_snapping(segments, points_to_snap)
    start_node = snap_results.get("start")
    target_node = snap_results.get("target")
    fac = {"lon": target_lon, "lat": target_lat, "name": facility_name, "capacity_score": cap}
    if start_node is None or target_node is None:
        direct_dist = np.sqrt((start_lon - target_lon)**2 + (start_lat - target_lat)**2) * 111
        composite = direct_dist - alpha * cap
        return _make_result(fac, direct_dist, composite, start_lon, start_lat)
    try:
        if start_node == target_node:
            total_dist = 0.0
            path_coords = [[start_lon, start_lat]]
        else:
            path = nx.astar_path(G, start_node, target_node, weight="weight")
            total_dist = 0
            path_coords = []
            for j in range(len(path) - 1):
                edge_data = G.get_edge_data(path[j], path[j + 1])
                total_dist += edge_data.get("distance_km", 0)
                if len(path_coords) == 0:
                    path_coords.append(list(path[j]))
                path_coords.append(list(path[j + 1]))
        composite = total_dist - alpha * cap
        return _make_result(fac, total_dist, composite, start_lon, start_lat, path_coords)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        direct_dist = np.sqrt((start_lon - target_lon)**2 + (start_lat - target_lat)**2) * 111
        composite = direct_dist - alpha * cap
        return _make_result(fac, direct_dist, composite, start_lon, start_lat)


def _make_result(fac, distance, composite, start_lon, start_lat, path_coords=None):
    if path_coords is None or len(path_coords) < 2:
        path_coords = [[start_lon, start_lat], [fac["lon"], fac["lat"]]]
    return {
        "facility_name": fac["name"],
        "facility_lon": fac["lon"],
        "facility_lat": fac["lat"],
        "distance_km": round(distance, 3),
        "capacity_score": round(fac["capacity_score"], 2),
        "composite_score": round(composite, 3),
        "route_geojson": {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": path_coords},
            "properties": {
                "facility_name": fac["name"],
                "distance_km": round(distance, 3),
                "capacity_score": round(fac["capacity_score"], 2),
                "composite_score": round(composite, 3),
            },
        },
    }
