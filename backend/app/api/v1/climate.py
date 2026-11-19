from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from backend.app.core.database import get_db
from backend.app.schemas.climate import (
    WeatherObservationResponse,
    ExposureIntervalResponse,
    ProviderStatus,
)
from backend.app.providers.weather.service import weather_service
from backend.app.climate.engine import ExposureCalculationEngine
from backend.app.api.deps import get_current_user, get_current_worker

router = APIRouter(prefix="/climate", tags=["Climate & Exposure"])

def _map_dto_to_response(obs) -> WeatherObservationResponse:
    is_demo = obs.provider_name.startswith("DEMO") or obs.validation_status == "DEMO_FIXTURE"
    hi = obs.heat_index_celsius
    risk = "LOW"
    if hi is not None:
        if hi >= 54.0:
            risk = "EXTREME_DANGER"
        elif hi >= 41.0:
            risk = "DANGER"
        elif hi >= 32.0:
            risk = "EXTREME_CAUTION"
        elif hi >= 27.0:
            risk = "CAUTION"

    station = obs.source_identifier
    if obs.raw_payload and isinstance(obs.raw_payload, dict):
        station = obs.raw_payload.get("station_name") or station

    return WeatherObservationResponse(
        id="current_observation",
        provider_name=obs.provider_name,
        source_identifier=obs.source_identifier,
        station_name=station,
        data_type=getattr(obs, "data_type", "DIRECT_STATION_OBSERVATION"),
        is_demo=is_demo,
        latitude=obs.latitude,
        longitude=obs.longitude,
        spatial_resolution_km=obs.spatial_resolution_km,
        observed_at=obs.observed_at,
        temperature_celsius=obs.temperature_celsius,
        temperature_c=obs.temperature_celsius,
        relative_humidity_pct=obs.relative_humidity_pct,
        heat_index_celsius=obs.heat_index_celsius,
        heat_index_c=obs.heat_index_celsius,
        wbgt_estimated_celsius=obs.wbgt_estimated_celsius,
        swbgt_proxy_c=obs.wbgt_estimated_celsius,
        risk_category=risk,
        wind_speed_mps=obs.wind_speed_mps,
        solar_radiation_wm2=obs.solar_radiation_wm2,
        confidence_score=obs.confidence_score,
        data_freshness_status=obs.data_freshness_status,
        validation_status=obs.validation_status,
    )

@router.get("/current", response_model=WeatherObservationResponse)
@router.get("/observations", response_model=WeatherObservationResponse)
async def get_current_weather_observation(
    lat: Optional[float] = Query(default=None, ge=-90.0, le=90.0),
    latitude: Optional[float] = Query(default=None, ge=-90.0, le=90.0),
    lon: Optional[float] = Query(default=None, ge=-180.0, le=180.0),
    longitude: Optional[float] = Query(default=None, ge=-180.0, le=180.0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    target_lat = lat if lat is not None else (latitude if latitude is not None else 17.3850)
    target_lon = lon if lon is not None else (longitude if longitude is not None else 78.4867)
    obs = await weather_service.get_current_observation(target_lat, target_lon, db=db)
    return _map_dto_to_response(obs)

@router.get("/shifts/{shift_id}/exposure", response_model=List[ExposureIntervalResponse])
async def compute_or_get_shift_exposure(
    shift_id: str,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    intervals = await ExposureCalculationEngine.compute_shift_exposure(
        db, shift_id, current_worker.id
    )
    return intervals

@router.get("/providers/status")
async def get_weather_providers_health(
    current_user = Depends(get_current_user),
):
    statuses = await weather_service.get_all_providers_status()
    return {"providers": statuses}
