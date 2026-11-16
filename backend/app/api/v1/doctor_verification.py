"""
Doctor Verification Workflow & Clinical EHR Updates Router
Provides:
- Retrieval of patient-submitted entries awaiting doctor verification
- Physician review (approve, reject, edit & approve)
- Direct physician EHR entries (diagnoses, medications, clinical notes)
- Audit log tracking of all verifications
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User
from backend.app.services.doctor_verification_service import DoctorVerificationService

router = APIRouter(prefix="/doctor-verification", tags=["Doctor Verification"])

class ReviewActionRequest(BaseModel):
    action: str  # "approve", "reject", "edit_and_approve"
    review_notes: Optional[str] = None
    edited_data: Optional[Dict[str, Any]] = None

class DirectClinicalEntryRequest(BaseModel):
    patient_id: str
    entry_type: str  # "diagnosis", "prescription", "note"
    data: Dict[str, Any]

@router.get("/pending")
def list_pending_verifications(
    doctor_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    status_filter: str = "pending_verification",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists pending unverified entries for doctor review."""
    return DoctorVerificationService.list_pending_updates(
        doctor_id=doctor_id,
        patient_id=patient_id,
        status_filter=status_filter,
        db=db
    )

@router.post("/{update_id}/review")
def review_pending_update(
    update_id: str,
    req: ReviewActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Doctor review action: approve, edit & approve, or reject."""
    if req.action not in ["approve", "reject", "edit_and_approve"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve', 'reject', or 'edit_and_approve'"
        )

    try:
        return DoctorVerificationService.review_update(
            update_id=update_id,
            action=req.action,
            reviewed_by=current_user.full_name or current_user.username,
            review_notes=req.review_notes,
            edited_data=req.edited_data,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/direct-entry", status_code=status.HTTP_201_CREATED)
def doctor_direct_entry(
    req: DirectClinicalEntryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allows physicians to directly add diagnoses, prescriptions, and clinical notes."""
    try:
        return DoctorVerificationService.doctor_direct_entry(
            patient_id=req.patient_id,
            entry_type=req.entry_type,
            doctor_name=current_user.full_name or current_user.username,
            data=req.data,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
