"""
Hospital Admission & Bed Management Router (100-Bed Facility)
Provides:
- Real-time 100-bed occupancy & ward breakdown
- Bed registration, categories, and availability filters
- Admission, ward transfer, and discharge workflows
- Integration with Scheduling Agent and Agent Event Bus
"""

from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.db.models import BedRegistry, AdmissionRequest
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User
from backend.app.services.agents.scheduling_agent import SchedulingAgent

router = APIRouter(prefix="/beds", tags=["Bed Management"])

class AdmissionCreateRequest(BaseModel):
    patient_id: str
    department: str
    recommended_ward: str
    priority: str = "routine"  # routine, urgent, emergency
    admission_notes: Optional[str] = None
    doctor_id: Optional[str] = None

class BedTransferRequest(BaseModel):
    request_id: str
    new_bed_id: str

class DischargeRequest(BaseModel):
    request_id: str

@router.get("/overview")
def get_bed_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns 100-bed facility overview and ward breakdown."""
    return SchedulingAgent.get_bed_overview(db)

@router.get("/list")
def list_beds(
    ward: Optional[str] = None,
    status_filter: Optional[str] = None,
    is_occupied: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists beds with optional ward and availability filtering."""
    stmt = select(BedRegistry)
    if ward:
        stmt = stmt.where(BedRegistry.ward == ward)
    if status_filter:
        stmt = stmt.where(BedRegistry.status == status_filter)
    if is_occupied is not None:
        stmt = stmt.where(BedRegistry.is_occupied == is_occupied)

    beds = db.scalars(stmt.order_by(BedRegistry.bed_number.asc())).all()
    return [
        {
            "bed_id": b.bed_id,
            "bed_number": b.bed_number,
            "ward": b.ward,
            "bed_type": b.bed_type,
            "is_occupied": b.is_occupied,
            "status": b.status,
            "current_patient_id": b.current_patient_id,
            "daily_charge": b.daily_charge,
            "notes": b.notes
        }
        for b in beds
    ]

@router.get("/admissions")
def list_admissions(
    status_filter: Optional[str] = None,
    patient_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists admission requests for nurses and doctors."""
    stmt = select(AdmissionRequest)
    if status_filter:
        stmt = stmt.where(AdmissionRequest.status == status_filter)
    if patient_id:
        stmt = stmt.where(AdmissionRequest.patient_id == patient_id)

    stmt = stmt.order_by(AdmissionRequest.created_at.desc())
    adms = db.scalars(stmt).all()
    return [
        {
            "request_id": a.request_id,
            "patient_id": a.patient_id,
            "doctor_id": a.doctor_id,
            "department": a.department,
            "recommended_ward": a.recommended_ward,
            "assigned_bed_id": a.assigned_bed_id,
            "priority": a.priority,
            "status": a.status,
            "admission_notes": a.admission_notes,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "discharged_at": a.discharged_at.isoformat() if a.discharged_at else None
        }
        for a in adms
    ]

@router.post("/admission", status_code=status.HTTP_201_CREATED)
def admit_patient(
    req: AdmissionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiates patient admission and allocates a bed."""
    try:
        return SchedulingAgent.create_admission_request(
            patient_id=req.patient_id,
            department=req.department,
            recommended_ward=req.recommended_ward,
            priority=req.priority,
            admission_notes=req.admission_notes,
            doctor_id=req.doctor_id,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/transfer")
def transfer_patient_bed(
    req: BedTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transfers admitted patient to a new bed."""
    try:
        return SchedulingAgent.transfer_bed(req.request_id, req.new_bed_id, db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/discharge")
def discharge_patient_bed(
    req: DischargeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Discharges patient and moves bed to cleaning status."""
    try:
        return SchedulingAgent.discharge_patient(req.request_id, db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
