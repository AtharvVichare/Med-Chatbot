"""
Hospital, Doctor Directory & Appointment Booking Router
Provides:
- Structured directory of verified doctors across medical disciplines
- Consultation timings and live slot availability
- Safe appointment booking preventing double-bookings
- Hospital profile and emergency contacts
"""

from typing import List, Optional
from datetime import date
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.db.models import DoctorProfile, AppointmentBooking, Patient
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User
from backend.app.services.agents.scheduling_agent import SchedulingAgent
from backend.app.services.hospital_service import HOSPITAL_DATABASE

router = APIRouter(prefix="/directory", tags=["Hospital & Doctor Directory"])

class BookAppointmentRequest(BaseModel):
    doctor_id: str
    booking_date: date
    time_slot: str
    chief_complaint: Optional[str] = None
    patient_id: Optional[str] = None

@router.get("/doctors")
def get_doctors_directory(
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves verified doctor profiles and open schedule slots."""
    return SchedulingAgent.get_available_doctors(department=department, db=db)

@router.get("/hospitals")
def get_hospitals_directory(
    current_user: User = Depends(get_current_user)
):
    """Returns verified tertiary hospitals, emergency lines, and ABDM registration protocols."""
    return list(HOSPITAL_DATABASE.values())

@router.get("/appointments")
def list_appointments(
    doctor_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists appointments with role-based visibility."""
    stmt = select(AppointmentBooking)

    # If patient, default to their own record unless admin/doctor
    if current_user.role == "patient" and current_user.patient_id:
        stmt = stmt.where(AppointmentBooking.patient_id == current_user.patient_id)
    else:
        if patient_id:
            stmt = stmt.where(AppointmentBooking.patient_id == patient_id)
        if doctor_id:
            stmt = stmt.where(AppointmentBooking.doctor_id == doctor_id)
        elif current_user.role == "doctor":
            # Find doctor_id corresponding to current doctor user
            doc = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == current_user.username))
            if doc:
                stmt = stmt.where(AppointmentBooking.doctor_id == doc.doctor_id)

    if status_filter:
        stmt = stmt.where(AppointmentBooking.status == status_filter)

    stmt = stmt.order_by(AppointmentBooking.booking_date.asc(), AppointmentBooking.time_slot.asc())
    appts = db.scalars(stmt).all()

    results = []
    for a in appts:
        pat = db.scalar(select(Patient).where(Patient.patient_id == a.patient_id))
        doc = db.scalar(select(DoctorProfile).where(DoctorProfile.doctor_id == a.doctor_id))
        hosp = a.hospital_name or (doc.hospital_name if doc else "Seth GS Medical College & KEM Hospital")
        token_num = f"TKT-{a.booking_date.strftime('%Y%m%d')}-{abs(hash(a.booking_id)) % 899 + 101}"
        chamber = f"Chamber {abs(hash(doc.name if doc else 'OPD')) % 15 + 101}, OPD Block B"
        results.append({
            "booking_id": a.booking_id,
            "token_number": token_num,
            "patient_id": a.patient_id,
            "patient_name": f"{pat.first_name} {pat.last_name}" if pat else a.patient_id,
            "doctor_id": a.doctor_id,
            "doctor_name": doc.name if doc else a.doctor_id,
            "qualification": doc.qualification if doc else "MBBS, MD",
            "department": a.department,
            "hospital_name": hosp,
            "chamber_room": chamber,
            "booking_date": str(a.booking_date),
            "time_slot": a.time_slot,
            "status": a.status,
            "chief_complaint": a.chief_complaint,
            "consultation_fee": doc.consultation_fee if doc else 800.0,
            "fee": doc.consultation_fee if doc else 800.0,
            "booked_via": a.booked_via,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
    return results

@router.post("/book-appointment", status_code=status.HTTP_201_CREATED)
def book_appointment(
    req: BookAppointmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Books an appointment slot, verifying doctor capacity and preventing double booking."""
    target_patient_id = req.patient_id or current_user.patient_id
    if not target_patient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target patient ID must be provided.")

    try:
        return SchedulingAgent.book_appointment(
            patient_id=target_patient_id,
            doctor_id=req.doctor_id,
            booking_date=req.booking_date,
            time_slot=req.time_slot,
            chief_complaint=req.chief_complaint,
            booked_via="portal" if current_user.role != "patient" else "intake_agent",
            db=db
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Booking failed: {str(e)}")

@router.delete("/appointments/{booking_id}")
def cancel_appointment(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancels a booked appointment slot."""
    appt = db.scalar(select(AppointmentBooking).where(AppointmentBooking.booking_id == booking_id))
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    appt.status = "cancelled"
    db.commit()
    return {"booking_id": booking_id, "status": "cancelled", "message": "Appointment cancelled successfully."}

class UpdateStatusRequest(BaseModel):
    status: str

@router.patch("/appointments/{booking_id}/status")
def update_appointment_status(
    booking_id: str,
    req: UpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates appointment status (e.g., confirmed, checked_in, completed, cancelled)."""
    appt = db.scalar(select(AppointmentBooking).where(AppointmentBooking.booking_id == booking_id))
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    appt.status = req.status
    db.commit()
    return {"booking_id": booking_id, "status": appt.status, "message": f"Appointment status updated to {req.status}."}
