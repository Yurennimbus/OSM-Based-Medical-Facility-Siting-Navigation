import os
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

DB_PATH = os.path.join(BASE_DIR, "backend", "webgis.db")
STATIC_DIR = os.path.join(BASE_DIR, "frontend")
DATA_DIR = os.path.join(BASE_DIR, "Data")

_yml = {}
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        _yml = yaml.safe_load(f) or {}

SERVER_HOST = _yml.get("server", {}).get("host", "0.0.0.0")
SERVER_PORT = _yml.get("server", {}).get("port", 8000)

GRID_CELL_SIZE = _yml.get("grid", {}).get("default_cell_size", 0.005)
GRID_MAX_CELLS = _yml.get("grid", {}).get("max_cells", 50000)

ROUTING_SNAP_TOLERANCE_M = _yml.get("routing", {}).get("snap_tolerance_m", 2000)
ROUTING_MAX_CANDIDATES = _yml.get("routing", {}).get("max_candidates", 30)
ROUTING_PADDING_DEG = _yml.get("routing", {}).get("local_road_padding_deg", 0.05)

MANDATORY_LAYERS = ["roads", "landuse", "health"]

ROAD_SPEED_MAP = {
    "motorway": 100, "motorway_link": 60,
    "trunk": 80, "trunk_link": 50,
    "primary": 60, "primary_link": 40,
    "secondary": 40, "secondary_link": 30,
    "tertiary": 30, "tertiary_link": 25,
    "unclassified": 20, "residential": 15,
    "service": 10, "track": 10,
    "pedestrian": 5, "path": 5,
    "unknown": 30,
}

CAPACITY_SCORE_DEFAULT = 1.0

SUPPORTED_EXTENSIONS = (".geojson", ".shp", ".gpkg")


def resolve_data_path(city_config_entry):
    source = city_config_entry.get("source", "")
    if not source:
        return None
    if os.path.isabs(source) and os.path.isdir(source):
        return source
    candidate = os.path.join(BASE_DIR, source)
    if os.path.isdir(candidate):
        return candidate
    for root in [os.path.dirname(BASE_DIR), BASE_DIR]:
        candidate = os.path.join(root, source)
        if os.path.isdir(candidate):
            return candidate
    return None


def get_city_config(schema_name):
    cities = _yml.get("cities") or {}
    return cities.get(schema_name, None)


def get_all_city_configs():
    return _yml.get("cities") or {}


def get_layer_config(schema_name, layer_name):
    city = get_city_config(schema_name)
    if not city:
        return None
    return city.get("layers", {}).get(layer_name, None)
