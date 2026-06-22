import json
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import func
from datetime import datetime
from .config import DB_PATH

Base = declarative_base()

class CityRegistry(Base):
    __tablename__ = "city_registry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    schema_name = Column(String(100), unique=True, nullable=False)
    data_path = Column(String(500), nullable=False)
    bounds = Column(Text, nullable=True)
    available_layers = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class FacilityCapacity(Base):
    __tablename__ = "facility_capacity"
    id = Column(Integer, primary_key=True, autoincrement=True)
    city_schema = Column(String(100), nullable=False)
    facility_name = Column(String(500), nullable=False)
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    capacity_score = Column(Float, default=1.0)
    category = Column(String(50), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    return _engine


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def register_city(name, schema_name, data_path, bounds=None, available_layers=None):
    session = get_session()
    existing = session.query(CityRegistry).filter_by(schema_name=schema_name).first()
    if existing:
        existing.name = name
        existing.data_path = data_path
        if bounds:
            existing.bounds = json.dumps(bounds) if isinstance(bounds, dict) else bounds
        if available_layers:
            existing.available_layers = json.dumps(available_layers) if isinstance(available_layers, list) else available_layers
        existing.is_active = True
    else:
        city = CityRegistry(
            name=name,
            schema_name=schema_name,
            data_path=data_path,
            bounds=json.dumps(bounds) if isinstance(bounds, dict) else bounds,
            available_layers=json.dumps(available_layers) if isinstance(available_layers, list) else available_layers,
        )
        session.add(city)
    session.commit()
    session.close()


def get_active_cities():
    session = get_session()
    cities = session.query(CityRegistry).filter_by(is_active=True).all()
    result = []
    for c in cities:
        result.append({
            "id": c.id,
            "name": c.name,
            "schema_name": c.schema_name,
            "data_path": c.data_path,
            "bounds": json.loads(c.bounds) if c.bounds else None,
            "available_layers": json.loads(c.available_layers) if c.available_layers else [],
            "is_active": c.is_active,
        })
    session.close()
    return result


def get_city_by_schema(schema_name):
    session = get_session()
    c = session.query(CityRegistry).filter_by(schema_name=schema_name, is_active=True).first()
    if not c:
        session.close()
        return None
    result = {
        "id": c.id,
        "name": c.name,
        "schema_name": c.schema_name,
        "data_path": c.data_path,
        "bounds": json.loads(c.bounds) if c.bounds else None,
        "available_layers": json.loads(c.available_layers) if c.available_layers else [],
    }
    session.close()
    return result


def upsert_facility_capacity(city_schema, facility_name, longitude, latitude, capacity_score, category=None):
    session = get_session()
    existing = session.query(FacilityCapacity).filter_by(
        city_schema=city_schema,
        facility_name=facility_name,
        longitude=longitude,
        latitude=latitude
    ).first()
    if existing:
        existing.capacity_score = capacity_score
        existing.updated_at = datetime.utcnow()
    else:
        fc = FacilityCapacity(
            city_schema=city_schema,
            facility_name=facility_name,
            longitude=longitude,
            latitude=latitude,
            capacity_score=capacity_score,
            category=category,
        )
        session.add(fc)
    session.commit()
    session.close()


def get_facility_capacities(city_schema):
    session = get_session()
    rows = session.query(FacilityCapacity).filter_by(city_schema=city_schema).all()
    result = {}
    for r in rows:
        key = (round(r.longitude, 6), round(r.latitude, 6))
        result[key] = r.capacity_score
    session.close()
    return result


def update_facility_capacity(city_schema, facility_name, new_score):
    session = get_session()
    rows = session.query(FacilityCapacity).filter_by(
        city_schema=city_schema, facility_name=facility_name
    ).all()
    for r in rows:
        r.capacity_score = new_score
        r.updated_at = datetime.utcnow()
    session.commit()
    count = len(rows)
    session.close()
    return count
