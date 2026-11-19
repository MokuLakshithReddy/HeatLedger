from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from backend.app.core.database import get_db
from backend.app.schemas.location import (
    LocationSampleCreate,
    LocationSampleBatch,
    LocationSampleResponse,
)
from backend.app.services.location_service import LocationService
from backend.app.api.deps import get_current_worker

router = APIRouter(prefix="/shifts", tags=["Location Tracking"])

@router.post("/{shift_id}/location-samples", response_model=LocationSampleResponse)
def record_location_sample(
    shift_id: str,
    sample_in: LocationSampleCreate,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    return LocationService.record_sample(db, shift_id, current_worker.id, sample_in)

@router.post("/{shift_id}/location-samples/batch", response_model=List[LocationSampleResponse])
def record_location_samples_batch(
    shift_id: str,
    batch_in: LocationSampleBatch,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    return LocationService.record_batch(db, shift_id, current_worker.id, batch_in.samples)

@router.get("/{shift_id}/location-samples", response_model=List[LocationSampleResponse])
def get_shift_location_samples(
    shift_id: str,
    limit: int = 500,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    return LocationService.get_shift_samples(db, shift_id, current_worker.id, limit=limit)
