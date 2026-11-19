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

@router.get("/observations", response_model=WeatherObservationResponse)
async def get_current_weather_observation(
    lat: float = Query(default=17.3850, ge=-90.0, le=90.0, description="Latitude (default Hyderabad)"),
    lon: float = Query(default=78.4867, ge=-180.0, le=180.0, description="Longitude (default Hyderabad)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    obs = await weather_service.get_current_observation(lat, lon, db=db)
    return WeatherObservationResponse(
        id="live_observation",
        provider_name=obs.provider_name,
        source_identifier=obs.source_identifier,
        latitude=obs.latitude,
        longitude=obs.longitude,
        spatial_resolution_km=obs.spatial_resolution_km,
        observed_at=obs.observed_at,
        temperature_celsius=obs.temperature_celsius,
        relative_humidity_pct=obs.relative_humidity_pct,
        heat_index_celsius=obs.heat_index_celsius,
        wbgt_estimated_celsius=obs.wbgt_estimated_celsius,
        wind_speed_mps=obs.wind_speed_mps,
        solar_radiation_wm2=obs.solar_radiation_wm2,
        confidence_score=obs.confidence_score,
        data_freshness_status=obs.data_freshness_status,
        validation_status=obs.validation_status,
    )

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
