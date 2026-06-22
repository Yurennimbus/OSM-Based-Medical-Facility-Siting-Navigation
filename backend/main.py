import os
import json as json_mod
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db, get_active_cities, get_city_by_schema, update_facility_capacity, get_facility_capacities, upsert_facility_capacity
from .importer import import_all_configured_cities, import_city_from_path, detect_layers, load_layer, load_boundary_layer
from .suitability import compute_suitability
from .routing import compute_routes, compute_route_to_facility
from .models import (
    SuitabilityRequest, NavigateRequest, NavigateToRequest, CapacityUpdateRequest,
    ScanDirectoryRequest, DynamicImportRequest, FacilityInfo,
)
from .config import STATIC_DIR, DATA_DIR
import pandas as pd
import re

VALID_SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_schema(schema_name):
    if not VALID_SCHEMA_RE.match(schema_name):
        raise HTTPException(400, f"Invalid schema name: '{schema_name}'. Use lowercase letters, digits, and underscores only (e.g., 'beijing').")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        from .database import get_session, CityRegistry
        session = get_session()
        existing = session.query(CityRegistry).filter_by(is_active=True).count()
        session.close()
        if existing == 0:
            print("No cities registered, importing from config...")
            import_all_configured_cities()
    except Exception as e:
        print(f"Startup: {e}")
    yield


app = FastAPI(title="WebGIS - Medical Facility Site Selection", version="2.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/cities")
def list_cities():
    return get_active_cities()


@app.get("/api/cities/{schema_name}")
def get_city(schema_name: str):
    c = get_city_by_schema(schema_name)
    if not c:
        raise HTTPException(404, "City not found")
    return c


@app.post("/api/cities/scan")
def scan_directory(req: ScanDirectoryRequest):
    path = req.directory_path
    if not os.path.isdir(path):
        raise HTTPException(400, f"Directory not found: {path}")
    layers = detect_layers(path)
    return {
        "directory": path,
        "layers": {k: {"feature_count": v["feature_count"], "geometry_type": v["geometry_type"], "fields": v["fields"]} for k, v in layers.items()},
        "has_mandatory": all(l in layers for l in ["health", "landuse", "roads"]),
    }


@app.post("/api/cities/import-dynamic")
def import_dynamic(req: DynamicImportRequest):
    _validate_schema(req.schema_name)
    try:
        return import_city_from_path(req.city_name, req.schema_name, req.directory_path)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/cities/reload")
def reload_cities():
    results = import_all_configured_cities()
    return {"imported": len(results), "cities": [r["schema_name"] for r in results]}


@app.post("/api/analyze/suitability")
def analyze_suitability(req: SuitabilityRequest):
    c = get_city_by_schema(req.city_schema)
    if not c:
        raise HTTPException(404, "City not found")
    try:
        return compute_suitability(
            c["data_path"], req.w_population, req.w_traffic,
            req.w_competition, req.w_landuse,
            req.facility_type, req.city_schema, req.grid_size,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/routing/navigate")
def navigate(req: NavigateRequest):
    c = get_city_by_schema(req.city_schema)
    if not c:
        raise HTTPException(404, "City not found")
    try:
        results = compute_routes(
            c["data_path"], req.start_lon, req.start_lat,
            req.facility_type, req.alpha, req.city_schema, req.max_results,
        )
        return {"routes": results, "parameters": {"alpha": req.alpha, "facility_type": req.facility_type}}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/routing/navigate-to")
def navigate_to(req: NavigateToRequest):
    c = get_city_by_schema(req.city_schema)
    if not c:
        raise HTTPException(404, "City not found")
    try:
        result = compute_route_to_facility(
            c["data_path"], req.start_lon, req.start_lat,
            req.target_lon, req.target_lat, req.alpha,
            req.city_schema, req.facility_name,
        )
        return {"route": result, "parameters": {"alpha": req.alpha}}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.put("/api/facilities/capacity")
def update_capacity(req: CapacityUpdateRequest):
    n = update_facility_capacity(req.city_schema, req.facility_name, req.capacity_score)
    if n == 0:
        raise HTTPException(404, "Facility not found")
    return {"updated": n}


@app.put("/api/facilities/capacity/batch")
def update_capacity_batch(req: list[FacilityInfo]):
    updated = 0
    for item in req:
        upsert_facility_capacity(
            city_schema=item.city_schema,
            facility_name=item.name,
            longitude=item.longitude,
            latitude=item.latitude,
            capacity_score=item.capacity_score,
            category=item.category,
        )
        updated += 1
    return {"updated": updated}


@app.get("/api/facilities/{city_schema}")
def list_facilities(city_schema: str):
    caps = get_facility_capacities(city_schema)
    return {"facilities": [{"lon": k[0], "lat": k[1], "capacity_score": v} for k, v in caps.items()]}


@app.get("/api/layers/{city_schema}/list")
def list_layers_for_city(city_schema: str):
    c = get_city_by_schema(city_schema)
    if not c:
        raise HTTPException(404, "City not found")
    layers = detect_layers(c["data_path"])
    return {
        "city_schema": city_schema,
        "layers": {k: {"feature_count": v["feature_count"], "geometry_type": v["geometry_type"]} for k, v in layers.items()},
    }


@app.get("/api/layers/{city_schema}/{layer_name}")
def get_layer_data(city_schema: str, layer_name: str):
    if layer_name == "list":
        return list_layers_for_city(city_schema)
    c = get_city_by_schema(city_schema)
    if not c:
        raise HTTPException(404, "City not found")
    gdf = load_layer(c["data_path"], layer_name)
    if gdf is None:
        raise HTTPException(404, f"Layer '{layer_name}' not found")
    return JSONResponse(content=json_mod.loads(gdf.to_json()))


@app.get("/api/health/{city_schema}/{lon}/{lat}")
def facility_detail(city_schema: str, lon: float, lat: float):
    c = get_city_by_schema(city_schema)
    if not c:
        raise HTTPException(404, "City not found")
    gdf = load_layer(c["data_path"], "health")
    if gdf is None:
        raise HTTPException(404, "Health layer not found")
    import numpy as np
    cx = gdf.geometry.x.values
    cy = gdf.geometry.y.values
    dx = (cx - lon) * 111000 * np.cos(np.radians(lat))
    dy = (cy - lat) * 111000
    gdf["_dist"] = np.sqrt(dx * dx + dy * dy)
    row = gdf.nsmallest(1, "_dist").iloc[0]
    props = {}
    for col in gdf.columns:
        if col in ("geometry", "_dist"):
            continue
        v = row[col]
        if hasattr(v, "item"):
            v = v.item()
        props[col] = str(v) if v is not None and not (isinstance(v, float) and pd.isna(v)) else None
    caps = get_facility_capacities(city_schema)
    key = (round(row.geometry.x, 6), round(row.geometry.y, 6))
    return {
        "facility": props,
        "longitude": float(row.geometry.x),
        "latitude": float(row.geometry.y),
        "capacity_score": caps.get(key, 1.0),
    }


if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
