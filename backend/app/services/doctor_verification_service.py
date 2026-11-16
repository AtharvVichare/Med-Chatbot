"""
Doctor Verification & Clinical Update Service for Aarogya-Drishti HMS.
Manages:
- Staging patient-shared information as pending unverified entries
- Doctor review (approve, edit & approve, reject)
- Appending doctor-approved data to verified longitudinal EHR
- Audit trails and provenance tracking
- Direct clinical updates from Doctor Dashboard (diagnoses, prescriptions, notes)
"""

import uuid
import json
import logging
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from backend.app.db.models import (
    PendingEHRUpdate,
    Patient,
    Condition,
    Medication,
    Observation,
    Allergy,
    AuditLog
)
from backend.app.services.agent_event_bus import AgentEventBus

logger = logging.getLogger("DoctorVerificationService")

class DoctorVerificationService:
    @staticmethod
    def stage_pending_update(
        patient_id: str,
        update_type: str,
        source: str,
        proposed_data: Dict[str, Any],
        assigned_doctor_id: Optional[str] = "DOC-CARD-001",
        source_reference_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Creates a pending, unverified entry in the queue for physician review."""
        update_id = f"PND-{uuid.uuid4().hex[:8].upper()}"
        now_utc = datetime.now(timezone.utc)

        entry = PendingEHRUpdate(
            update_id=update_id,
            patient_id=patient_id,
            update_type=update_type,
            source=source,
            source_reference_id=source_reference_id,
            proposed_data=json.dumps(proposed_data),
            status="pending_verification",
            assigned_doctor_id=assigned_doctor_id,
            created_at=now_utc
        )
        db.add(entry)
        db.commit()

        # Emit event notifying doctor
        AgentEventBus.emit(
            source_agent="patient_assistant",
            event_type="PENDING_EHR_VERIFICATION_STAGED",
            payload={
                "update_id": update_id,
                "patient_id": patient_id,
                "update_type": update_type,
                "source": source,
                "assigned_doctor_id": assigned_doctor_id,
                "data": proposed_data
            },
            target_agent="doctor_dashboard",
            requires_human_approval=True,
            db=db
        )

        return {
            "update_id": update_id,
            "status": "pending_verification",
            "message": "Information safely saved as pending review. Your doctor will verify this before it is appended to your longitudinal EHR."
        }

    @staticmethod
    def list_pending_updates(
        doctor_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        status_filter: str = "pending_verification",
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Lists pending entries awaiting verification."""
        stmt = select(PendingEHRUpdate)
        if status_filter:
            stmt = stmt.where(PendingEHRUpdate.status == status_filter)
        if doctor_id:
            stmt = stmt.where(PendingEHRUpdate.assigned_doctor_id == doctor_id)
        if patient_id:
            stmt = stmt.where(PendingEHRUpdate.patient_id == patient_id)

        stmt = stmt.order_by(PendingEHRUpdate.created_at.desc())
        entries = db.scalars(stmt).all()

        results = []
        for e in entries:
            try:
                data = json.loads(e.proposed_data)
            except Exception:
                data = e.proposed_data

            pat = db.scalar(select(Patient).where(Patient.patient_id == e.patient_id))
            patient_name = f"{pat.first_name} {pat.last_name}" if pat else e.patient_id

            results.append({
                "update_id": e.update_id,
                "patient_id": e.patient_id,
                "patient_name": patient_name,
                "update_type": e.update_type,
                "source": e.source,
                "proposed_data": data,
                "status": e.status,
                "assigned_doctor_id": e.assigned_doctor_id,
                "reviewed_by": e.reviewed_by,
                "review_notes": e.review_notes,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "reviewed_at": e.reviewed_at.isoformat() if e.reviewed_at else None
            })
        return results

    @staticmethod
    def review_update(
        update_id: str,
        action: str,  # "approve", "reject", "edit_and_approve"
        reviewed_by: str,
        review_notes: Optional[str] = None,
        edited_data: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Executes doctor review.
        If approved (or edited & approved), appends the validated entity to the verified EHR tables.
        """
        entry = db.scalar(select(PendingEHRUpdate).where(PendingEHRUpdate.update_id == update_id))
        if not entry:
            raise ValueError(f"Pending update {update_id} not found")

        now_utc = datetime.now(timezone.utc)
        payload = edited_data if edited_data else json.loads(entry.proposed_data)

        if action in ["approve", "edit_and_approve"]:
            entry.status = "approved" if action == "approve" else "edited_and_approved"
            entry.reviewed_by = reviewed_by
            entry.reviewed_at = now_utc
            entry.review_notes = review_notes

            # Append to verified longitudinal tables based on update_type
            if entry.update_type == "condition":
                cond_id = f"CND-{uuid.uuid4().hex[:8].upper()}"
                db.add(Condition(
                    condition_id=cond_id,
                    patient_id=entry.patient_id,
                    diagnosis_code=payload.get("diagnosis_code", "R69"),
                    diagnosis_name=payload.get("diagnosis_name", "Clinical Observation"),
                    onset_date=date.fromisoformat(payload.get("onset_date", str(date.today()))),
                    clinical_status="active",
                    is_synthetic=False,
                    created_at=now_utc
                ))
            elif entry.update_type == "medication":
                med_id = f"MED-{uuid.uuid4().hex[:8].upper()}"
                db.add(Medication(
                    medication_id=med_id,
                    encounter_id=entry.encounter_id or f"ENC-VERIFIED-{uuid.uuid4().hex[:6].upper()}",
                    patient_id=entry.patient_id,
                    medication_code=payload.get("medication_code", "OTC-VERIFIED"),
                    medication_name=payload.get("medication_name", "Prescribed Medication"),
                    dosage=payload.get("dosage", "As directed"),
                    start_date=date.fromisoformat(payload.get("start_date", str(date.today()))),
                    status="active",
                    is_synthetic=False,
                    created_at=now_utc
                ))
            elif entry.update_type == "observation":
                obs_id = f"OBS-{uuid.uuid4().hex[:8].upper()}"
                db.add(Observation(
                    observation_id=obs_id,
                    encounter_id=entry.encounter_id or f"ENC-OBS-{uuid.uuid4().hex[:6].upper()}",
                    patient_id=entry.patient_id,
                    test_code=payload.get("test_code", "HOME-MON"),
                    test_name=payload.get("test_name", "Home Clinical Measurement"),
                    value_numeric=payload.get("value_numeric"),
                    value_text=str(payload.get("value_text", "")),
                    unit=payload.get("unit"),
                    reference_range=payload.get("reference_range"),
                    interpretation=payload.get("interpretation", "Normal"),
                    date=date.fromisoformat(payload.get("date", str(date.today()))),
                    is_synthetic=False,
                    created_at=now_utc
                ))
            elif entry.update_type == "allergy":
                db.add(Allergy(
                    allergy_id=f"ALG-{uuid.uuid4().hex[:8].upper()}",
                    patient_id=entry.patient_id,
                    substance=payload.get("substance", "Unknown"),
                    reaction=payload.get("reaction", "Mild"),
                    severity=payload.get("severity", "moderate"),
                    verification_status="clinician_confirmed",
                    recorded_date=date.today(),
                    notes=f"Confirmed by Dr. {reviewed_by}: {review_notes or ''}",
                    created_at=now_utc
                ))

            # Audit log
            db.add(AuditLog(
                log_id=f"AUD-{uuid.uuid4().hex[:10].upper()}",
                user_id=reviewed_by,
                action="DOCTOR_APPROVED_EHR_APPEND",
                record_id=entry.update_id,
                record_type=f"verified_{entry.update_type}",
                facility="Aarogya HMS Clinical Portal",
                timestamp=now_utc,
                is_synthetic=False
            ))

        elif action == "reject":
            entry.status = "rejected"
            entry.reviewed_by = reviewed_by
            entry.reviewed_at = now_utc
            entry.review_notes = review_notes or "Rejected by physician"

            db.add(AuditLog(
                log_id=f"AUD-{uuid.uuid4().hex[:10].upper()}",
                user_id=reviewed_by,
                action="DOCTOR_REJECTED_EHR_ENTRY",
                record_id=entry.update_id,
                record_type=f"rejected_{entry.update_type}",
                facility="Aarogya HMS Clinical Portal",
                timestamp=now_utc,
                is_synthetic=False
            ))

        db.commit()

        # Emit bus event
        AgentEventBus.emit(
            source_agent="doctor_verification_service",
            event_type="EHR_VERIFICATION_DECIDED",
            payload={
                "update_id": entry.update_id,
                "patient_id": entry.patient_id,
                "action": action,
                "status": entry.status,
                "doctor": reviewed_by,
                "notes": review_notes
            },
            target_agent="patient_dashboard",
            requires_human_approval=False,
            db=db
        )

        return {
            "update_id": entry.update_id,
            "status": entry.status,
            "reviewed_by": entry.reviewed_by,
            "reviewed_at": entry.reviewed_at.isoformat(),
            "notes": entry.review_notes
        }

    @staticmethod
    def doctor_direct_entry(
        patient_id: str,
        entry_type: str,
        doctor_name: str,
        data: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Allows doctors to directly update diagnoses, prescriptions, and notes into verified EHR."""
        now_utc = datetime.now(timezone.utc)

        if entry_type == "diagnosis":
            cond_id = f"CND-{uuid.uuid4().hex[:8].upper()}"
            db.add(Condition(
                condition_id=cond_id,
                patient_id=patient_id,
                diagnosis_code=data.get("diagnosis_code", "R69"),
                diagnosis_name=data.get("diagnosis_name"),
                onset_date=date.fromisoformat(data.get("onset_date", str(date.today()))),
                clinical_status=data.get("clinical_status", "active"),
                is_synthetic=False,
                created_at=now_utc
            ))
        elif entry_type == "prescription":
            med_id = f"MED-{uuid.uuid4().hex[:8].upper()}"
            db.add(Medication(
                medication_id=med_id,
                encounter_id=f"ENC-{uuid.uuid4().hex[:6].upper()}",
                patient_id=patient_id,
                medication_code=data.get("medication_code", "RX-CLINICAL"),
                medication_name=data.get("medication_name"),
                dosage=data.get("dosage", "1 tablet daily"),
                start_date=date.fromisoformat(data.get("start_date", str(date.today()))),
                status="active",
                is_synthetic=False,
                created_at=now_utc
            ))

        db.add(AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:10].upper()}",
            user_id=doctor_name,
            action=f"DIRECT_CLINICAL_ENTRY_{entry_type.upper()}",
            record_id=patient_id,
            record_type="verified_clinical_entry",
            facility="Aarogya HMS",
            timestamp=now_utc,
            is_synthetic=False
        ))
        db.commit()

        return {
            "status": "success",
            "entry_type": entry_type,
            "patient_id": patient_id,
            "doctor": doctor_name
        }
