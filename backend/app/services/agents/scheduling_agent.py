"""
Scheduling Agent for Aarogya-Drishti HMS.
Manages:
- Doctor consultation bookings & slots
- Prevention of double bookings
- 100-bed facility allocation across 10 wards
- Admission, transfer, and discharge workflows
- Coordination with hospital departments via Agent Event Bus
"""

import uuid
import json
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from backend.app.db.models import (
    BedRegistry,
    DoctorProfile,
    AppointmentBooking,
    AdmissionRequest,
    Patient,
    Encounter
)
from backend.app.services.agent_event_bus import AgentEventBus

logger = logging.getLogger("SchedulingAgent")

class SchedulingAgent:
    @staticmethod
    def get_available_doctors(department: Optional[str] = None, db: Session = None) -> List[Dict[str, Any]]:
        """Retrieves verified doctor profiles and their schedule slots."""
        stmt = select(DoctorProfile).where(DoctorProfile.is_available == True)
        if department:
            stmt = stmt.where(func.lower(DoctorProfile.department) == department.lower().strip())

        docs = db.scalars(stmt).all()
        results = []
        for d in docs:
            slots = json.loads(d.schedule_json) if d.schedule_json else []
            results.append({
                "doctor_id": d.doctor_id,
                "name": d.name,
                "department": d.department,
                "specialty": d.specialty,
                "qualification": d.qualification,
                "experience_years": d.experience_years,
                "consultation_fee": d.consultation_fee,
                "hospital_name": d.hospital_name or "Seth GS Medical College & KEM Hospital",
                "is_available": d.is_available,
                "available_slots": slots
            })
        return results

    @staticmethod
    def check_slot_availability(doctor_id: str, booking_date: date, time_slot: str, db: Session) -> bool:
        """Verifies if a specific doctor slot is open without collision."""
        existing = db.scalar(
            select(AppointmentBooking).where(
                and_(
                    AppointmentBooking.doctor_id == doctor_id,
                    AppointmentBooking.booking_date == booking_date,
                    AppointmentBooking.time_slot == time_slot,
                    AppointmentBooking.status != "cancelled"
                )
            )
        )
        return existing is None

    @staticmethod
    def book_appointment(
        patient_id: str,
        doctor_id: str,
        booking_date: date,
        time_slot: str,
        chief_complaint: Optional[str] = None,
        booked_via: str = "intake_agent",
        db: Session = None
    ) -> Dict[str, Any]:
        """Books an appointment, validating doctor existence and preventing double bookings."""
        doctor = db.scalar(select(DoctorProfile).where(DoctorProfile.doctor_id == doctor_id))
        if not doctor:
            raise ValueError(f"Doctor {doctor_id} not found in hospital directory.")

        patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id))
        if not patient:
            raise ValueError(f"Patient {patient_id} not found.")

        # Double-booking guard
        if not SchedulingAgent.check_slot_availability(doctor_id, booking_date, time_slot, db):
            raise ValueError(f"Time slot '{time_slot}' on {booking_date} with {doctor.name} is already booked.")

        booking_id = f"BKG-{uuid.uuid4().hex[:8].upper()}"
        now_utc = datetime.now(timezone.utc)
        hosp_name = doctor.hospital_name or "Seth GS Medical College & KEM Hospital"
        booking = AppointmentBooking(
            booking_id=booking_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            department=doctor.department,
            hospital_name=hosp_name,
            booking_date=booking_date,
            time_slot=time_slot,
            status="confirmed",
            chief_complaint=chief_complaint,
            booked_via=booked_via,
            created_at=now_utc
        )
        db.add(booking)
        db.commit()

        # Generate realistic token number and chamber room for official ticket
        token_num = f"TKT-{booking_date.strftime('%Y%m%d')}-{abs(hash(booking_id)) % 899 + 101}"
        chamber_num = abs(hash(doctor.name)) % 15 + 101
        chamber_room = f"Chamber {chamber_num}, OPD Block B"

        # Emit inter-agent event to BOTH doctor_dashboard and nurse_dashboard
        payload = {
            "booking_id": booking_id,
            "token_number": token_num,
            "patient_id": patient_id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "doctor_name": doctor.name,
            "qualification": doctor.qualification,
            "department": doctor.department,
            "hospital_name": hosp_name,
            "chamber_room": chamber_room,
            "booking_date": str(booking_date),
            "time_slot": time_slot,
            "consultation_fee": doctor.consultation_fee
        }

        AgentEventBus.emit(
            source_agent="scheduling_agent",
            event_type="APPOINTMENT_CONFIRMED",
            payload=payload,
            target_agent="doctor_dashboard",
            requires_human_approval=False,
            db=db
        )

        AgentEventBus.emit(
            source_agent="scheduling_agent",
            event_type="APPOINTMENT_CONFIRMED",
            payload=payload,
            target_agent="nurse_dashboard",
            requires_human_approval=False,
            db=db
        )

        return {
            "booking_id": booking_id,
            "token_number": token_num,
            "status": "confirmed",
            "patient_id": patient_id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "doctor_id": doctor.doctor_id,
            "doctor_name": doctor.name,
            "qualification": doctor.qualification,
            "department": doctor.department,
            "specialty": doctor.specialty,
            "hospital_name": hosp_name,
            "chamber_room": chamber_room,
            "booking_date": str(booking_date),
            "time_slot": time_slot,
            "fee": doctor.consultation_fee,
            "chief_complaint": chief_complaint,
            "booked_via": booked_via,
            "created_at": now_utc.isoformat()
        }

    # ==========================================
    # Bed Management & Hospital Admissions
    # ==========================================
    @staticmethod
    def get_bed_overview(db: Session) -> Dict[str, Any]:
        """Returns 100-bed facility statistics and ward breakdown."""
        beds = db.scalars(select(BedRegistry).order_by(BedRegistry.bed_number.asc())).all()
        total = len(beds)
        occupied = sum(1 for b in beds if b.is_occupied)
        available = sum(1 for b in beds if b.status == "available")
        cleaning = sum(1 for b in beds if b.status == "cleaning")
        maintenance = sum(1 for b in beds if b.status == "maintenance")

        wards = {}
        for b in beds:
            if b.ward not in wards:
                wards[b.ward] = {"ward": b.ward, "total": 0, "occupied": 0, "available": 0, "beds": []}
            wards[b.ward]["total"] += 1
            if b.is_occupied:
                wards[b.ward]["occupied"] += 1
            elif b.status == "available":
                wards[b.ward]["available"] += 1
            wards[b.ward]["beds"].append({
                "bed_id": b.bed_id,
                "bed_number": b.bed_number,
                "ward": b.ward,
                "bed_type": b.bed_type,
                "is_occupied": b.is_occupied,
                "status": b.status,
                "current_patient_id": b.current_patient_id,
                "daily_charge": b.daily_charge
            })

        occupancy_rate = round((occupied / total * 100), 1) if total > 0 else 0.0
        return {
            "total_beds": total,
            "occupied_beds": occupied,
            "available_beds": available,
            "cleaning_beds": cleaning,
            "maintenance_beds": maintenance,
            "occupancy_rate": occupancy_rate,
            "wards": list(wards.values())
        }

    @staticmethod
    def find_available_bed(ward: Optional[str] = None, bed_type: Optional[str] = None, db: Session = None) -> Optional[BedRegistry]:
        """Finds the next available bed matching clinical requirements."""
        stmt = select(BedRegistry).where(
            and_(
                BedRegistry.is_occupied == False,
                BedRegistry.status == "available"
            )
        )
        if ward:
            stmt = stmt.where(func.lower(BedRegistry.ward) == ward.lower().strip())
        if bed_type:
            stmt = stmt.where(func.lower(BedRegistry.bed_type) == bed_type.lower().strip())

        return db.scalar(stmt)

    @staticmethod
    def create_admission_request(
        patient_id: str,
        department: str,
        recommended_ward: str,
        priority: str = "routine",
        admission_notes: Optional[str] = None,
        doctor_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Coordinates patient admission with bed availability."""
        patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id))
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        # Find bed in requested ward
        bed = SchedulingAgent.find_available_bed(ward=recommended_ward, db=db)
        assigned_bed_id = bed.bed_id if bed else None

        req_id = f"ADM-{uuid.uuid4().hex[:8].upper()}"
        now_utc = datetime.now(timezone.utc)
        adm = AdmissionRequest(
            request_id=req_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            department=department,
            recommended_ward=recommended_ward,
            assigned_bed_id=assigned_bed_id,
            priority=priority,
            status="assigned" if bed else "pending",
            admission_notes=admission_notes,
            created_at=now_utc
        )
        db.add(adm)

        if bed:
            bed.is_occupied = True
            bed.status = "occupied"
            bed.current_patient_id = patient_id
            bed.updated_at = now_utc

        db.commit()

        # Emit inter-agent event
        AgentEventBus.emit(
            source_agent="scheduling_agent",
            event_type="ADMISSION_REQUEST_PROCESSED",
            payload={
                "request_id": req_id,
                "patient_id": patient_id,
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "department": department,
                "ward": recommended_ward,
                "assigned_bed": bed.bed_number if bed else "WAITLIST",
                "priority": priority,
                "status": adm.status
            },
            target_agent="nurse_dashboard",
            requires_human_approval=(priority == "emergency"),
            db=db
        )

        return {
            "request_id": req_id,
            "patient_id": patient_id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "ward": recommended_ward,
            "assigned_bed": bed.bed_number if bed else None,
            "status": adm.status,
            "priority": priority
        }

    @staticmethod
    def transfer_bed(request_id: str, new_bed_id: str, db: Session) -> Dict[str, Any]:
        """Transfers an admitted patient to a new bed."""
        adm = db.scalar(select(AdmissionRequest).where(AdmissionRequest.request_id == request_id))
        if not adm:
            raise ValueError(f"Admission request {request_id} not found")

        old_bed = db.scalar(select(BedRegistry).where(BedRegistry.bed_id == adm.assigned_bed_id)) if adm.assigned_bed_id else None
        new_bed = db.scalar(select(BedRegistry).where(BedRegistry.bed_id == new_bed_id))
        if not new_bed:
            raise ValueError(f"Target bed {new_bed_id} not found")
        if new_bed.is_occupied:
            raise ValueError(f"Target bed {new_bed.bed_number} is already occupied")

        now_utc = datetime.now(timezone.utc)
        if old_bed:
            old_bed.is_occupied = False
            old_bed.current_patient_id = None
            old_bed.status = "cleaning"  # Set to cleaning protocol
            old_bed.updated_at = now_utc

        new_bed.is_occupied = True
        new_bed.current_patient_id = adm.patient_id
        new_bed.status = "occupied"
        new_bed.updated_at = now_utc

        adm.assigned_bed_id = new_bed.bed_id
        adm.recommended_ward = new_bed.ward
        db.commit()

        AgentEventBus.emit(
            source_agent="scheduling_agent",
            event_type="BED_TRANSFER_COMPLETED",
            payload={
                "request_id": request_id,
                "patient_id": adm.patient_id,
                "from_bed": old_bed.bed_number if old_bed else "None",
                "to_bed": new_bed.bed_number,
                "ward": new_bed.ward
            },
            target_agent="nurse_dashboard",
            db=db
        )

        return {
            "request_id": request_id,
            "from_bed": old_bed.bed_number if old_bed else None,
            "to_bed": new_bed.bed_number,
            "ward": new_bed.ward,
            "status": "transferred"
        }

    @staticmethod
    def discharge_patient(request_id: str, db: Session) -> Dict[str, Any]:
        """Discharges a patient and releases the bed into cleaning status."""
        adm = db.scalar(select(AdmissionRequest).where(AdmissionRequest.request_id == request_id))
        if not adm:
            raise ValueError(f"Admission request {request_id} not found")

        now_utc = datetime.now(timezone.utc)
        adm.status = "discharged"
        adm.discharged_at = now_utc

        bed_number = None
        if adm.assigned_bed_id:
            bed = db.scalar(select(BedRegistry).where(BedRegistry.bed_id == adm.assigned_bed_id))
            if bed:
                bed_number = bed.bed_number
                bed.is_occupied = False
                bed.current_patient_id = None
                bed.status = "cleaning"
                bed.updated_at = now_utc

        db.commit()

        # Trigger billing agent event
        AgentEventBus.emit(
            source_agent="scheduling_agent",
            event_type="PATIENT_DISCHARGED",
            payload={
                "request_id": request_id,
                "patient_id": adm.patient_id,
                "bed_number": bed_number,
                "discharged_at": now_utc.isoformat()
            },
            target_agent="billing_rcm_agent",
            requires_human_approval=False,
            db=db
        )

        return {
            "request_id": request_id,
            "status": "discharged",
            "bed_released": bed_number,
            "discharged_at": now_utc.isoformat()
        }
