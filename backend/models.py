from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re

SCHEMA_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class SuitabilityRequest(BaseModel):
    city_schema: str = Field(..., description="City schema identifier")
    facility_type: str = Field(..., description="Target facility type (hospital, clinic, pharmacy)")
    w_population: float = Field(0.25, ge=0.0, le=1.0, description="Weight for population factor")
    w_traffic: float = Field(0.25, ge=0.0, le=1.0, description="Weight for traffic accessibility")
    w_competition: float = Field(0.25, ge=0.0, le=1.0, description="Weight for competition (inverted)")
    w_landuse: float = Field(0.25, ge=0.0, le=1.0, description="Weight for landuse suitability")
    grid_size: Optional[float] = Field(0.005, description="Grid cell size in degrees")


class NavigateRequest(BaseModel):
    city_schema: str = Field(..., description="City schema identifier")
    start_lon: float = Field(..., description="Start longitude (WGS84)")
    start_lat: float = Field(..., description="Start latitude (WGS84)")
    facility_type: str = Field("hospital", description="Target facility type")
    alpha: float = Field(0.5, ge=0.0, le=2.0, description="Capacity weight in composite score")
    max_results: int = Field(3, ge=1, le=10, description="Number of candidate routes to return")


class NavigateToRequest(BaseModel):
    city_schema: str = Field(..., description="City schema identifier")
    start_lon: float = Field(..., description="Start longitude (WGS84)")
    start_lat: float = Field(..., description="Start latitude (WGS84)")
    target_lon: float = Field(..., description="Target facility longitude")
    target_lat: float = Field(..., description="Target facility latitude")
    facility_name: Optional[str] = Field("Target", description="Target facility name for display")
    alpha: float = Field(0.5, ge=0.0, le=2.0, description="Capacity weight in composite score")


class CapacityUpdateRequest(BaseModel):
    city_schema: str
    facility_name: str
    capacity_score: float = Field(..., ge=0.0, description="New capacity score")


class CapacityBatchUpdateRequest(BaseModel):
    city_schema: str
    facilities: List["FacilityInfo"]


class CityImportRequest(BaseModel):
    city_name: str = Field(..., min_length=1, description="Display name of the city")
    schema_name: str = Field(..., min_length=1, max_length=64, description="Unique schema identifier (lowercase letters, digits, underscores only)")
    data_path: str = Field(..., min_length=1, description="Path to directory containing GeoJSON files")

    @field_validator("schema_name")
    @classmethod
    def validate_schema_name(cls, v):
        if not SCHEMA_NAME_RE.match(v):
            raise ValueError("schema_name must start with a letter and contain only lowercase letters, digits, and underscores (e.g., 'beijing')")
        return v


class ScanDirectoryRequest(BaseModel):
    directory_path: str = Field(..., description="Path to scan for GeoJSON files")


class DynamicImportRequest(BaseModel):
    city_name: str = Field(..., min_length=1, description="Display name of the city")
    schema_name: str = Field(..., min_length=1, max_length=64, description="Unique schema identifier (lowercase letters, digits, underscores only)")
    directory_path: str = Field(..., min_length=1, description="Path to directory containing GeoJSON files")

    @field_validator("schema_name")
    @classmethod
    def validate_schema_name(cls, v):
        if not SCHEMA_NAME_RE.match(v):
            raise ValueError("schema_name must start with a letter and contain only lowercase letters, digits, and underscores (e.g., 'beijing')")
        return v


class LayerInfo(BaseModel):
    name: str
    feature_count: int
    geometry_type: str
    fields: List[str]


class CityInfo(BaseModel):
    name: str
    schema_name: str
    bounds: Optional[List[float]] = None
    available_layers: List[str] = []


class FacilityInfo(BaseModel):
    name: str
    longitude: float
    latitude: float
    category: str = "unknown"
    capacity_score: float = 1.0
    city_schema: Optional[str] = None


class RouteResult(BaseModel):
    facility_name: str
    facility_lon: float
    facility_lat: float
    distance_km: float
    capacity_score: float
    composite_score: float
    route_geojson: Optional[dict] = None


class SuitabilityResult(BaseModel):
    city_schema: str
    grid_geojson: dict
    top5_grids: List[dict]
    parameters: dict
