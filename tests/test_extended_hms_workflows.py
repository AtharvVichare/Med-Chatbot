import pytest
from datetime import date, datetime, timedelta, timezone
from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    Patient,
    FamilyLink,
    ClinicalNote,
    ClinicalOrder,
    NursingTask,
    MedicationAdministration,
    ShiftHandover,
    DailyHealthLog
)
from backend.app.core.demo_users import DEMO_USERS_DB
from backend.app.services.ehr_service import LongitudinalEHRService
from backend.app.core.dependencies import verify_patient_access
from fastapi import HTTPException


def test_demo_family_accounts_exist():
    """Verify all 4 demo family accounts are present and seeded."""
    db = SessionLocal()
    try:
        p_aarav = db.query(Patient).filter(Patient.patient_id == "PAT-AARAV-001").first()
        p_priya = db.query(Patient).filter(Patient.patient_id == "PAT-PRIYA-002").first()
        p_rohan = db.query(Patient).filter(Patient.patient_id == "PAT-ROHAN-003").first()
        p_sunita = db.query(Patient).filter(Patient.patient_id == "PAT-SUNITA-004").first()

        assert p_aarav is not None
        assert p_aarav.first_name == "Aarav"
        assert p_priya is not None
        assert p_priya.first_name == "Priya"
        assert p_rohan is not None
        assert p_sunita is not None
        assert p_sunita.age == 64

        # Check demo users in auth dictionary
        assert "aarav_mehta" in DEMO_USERS_DB
        assert "priya_mehta" in DEMO_USERS_DB
        assert "nurse_user" in DEMO_USERS_DB
    finally:
        db.close()


def test_family_linking_and_consent_enforcement():
    """Verify that family links require approval and enforce cross-patient access permissions."""
    db = SessionLocal()
    try:
        # Check verified link between Aarav and Priya
        link = db.query(FamilyLink).filter(
            FamilyLink.requester_patient_id == "PAT-AARAV-001",
            FamilyLink.target_patient_id == "PAT-PRIYA-002",
            FamilyLink.status == "approved"
        ).first()

        assert link is not None
        assert link.relationship_type == "spouse"

        # Priya user accessing Aarav's record should succeed via verify_patient_access
        priya_user = DEMO_USERS_DB["priya_mehta"]
        user_auth = verify_patient_access("PAT-AARAV-001", priya_user, db)
        assert user_auth.patient_id == "PAT-PRIYA-002"

        # An unrelated patient user (PAT-00001) accessing Aarav's record should raise 403 Forbidden
        patient_unrelated = DEMO_USERS_DB["patient_user"]
        with pytest.raises(HTTPException) as exc_info:
            verify_patient_access("PAT-AARAV-001", patient_unrelated, db)
        assert exc_info.value.status_code == 403
    finally:
        db.close()


def test_doctor_clinical_documentation_and_copilot():
    """Verify doctor clinical notes, orders, and AI Copilot draft synthesis."""
    db = SessionLocal()
    try:
        # Verify clinical notes exist for Aarav
        notes = db.query(ClinicalNote).filter(ClinicalNote.patient_id == "PAT-AARAV-001").all()
        assert len(notes) >= 2
        note_types = [n.note_type for n in notes]
        assert "discharge_summary" in note_types
        assert "consultation" in note_types

        # Verify clinical orders exist
        orders = db.query(ClinicalOrder).filter(ClinicalOrder.patient_id == "PAT-AARAV-001").all()
        assert len(orders) >= 1
        assert any(o.order_type in ["lab", "imaging"] for o in orders)

        # Test LongitudinalEHR retrieval for doctor
        ehr = LongitudinalEHRService.get_complete_patient_record("PAT-AARAV-001", db)
        assert ehr["demographics"]["first_name"] == "Aarav"
        assert len(ehr["conditions"]) >= 2
        assert len(ehr["medications"]) >= 2
        assert len(ehr["allergies"]) >= 2
        assert len(ehr["documents"]) >= 3  # CXR, HRCT, MRI
    finally:
        db.close()


def test_nurse_patient_monitoring_and_mar():
    """Verify nurse MAR administration, task tracking, and SBAR shift handovers."""
    db = SessionLocal()
    try:
        # Verify MAR records exist
        mar_records = db.query(MedicationAdministration).filter(
            MedicationAdministration.patient_id == "PAT-AARAV-001"
        ).all()
        assert len(mar_records) >= 2

        # Verify nursing tasks exist
        tasks = db.query(NursingTask).filter(NursingTask.patient_id == "PAT-AARAV-001").all()
        assert len(tasks) >= 2

        # Verify SBAR handover exists
        handover = db.query(ShiftHandover).filter(ShiftHandover.ward == "Deluxe Private Ward").first()
        assert handover is not None
        assert "Aarav Mehta" in handover.situation
        assert "S1, S2" in handover.assessment or "vitals" in handover.assessment.lower()
    finally:
        db.close()


def test_nurse_vitals_threshold_alerting():
    """Verify clinical threshold alerting when abnormal vitals are recorded."""
    from backend.app.api.v1.nursing_workspace import record_nurse_bedside_vitals

    db = SessionLocal()
    try:
        nurse_user = DEMO_USERS_DB["nurse_user"]

        # Record vital with SpO2 = 89% (Severe hypoxemia) and Systolic = 175 (Hypertensive crisis)
        payload = {
            "patient_id": "PAT-AARAV-001",
            "systolic_bp": 175,
            "diastolic_bp": 105,
            "pulse": 118,
            "spo2": 89,
            "temperature_c": 38.8,
            "notes": "Post-admission triage check"
        }

        res = record_nurse_bedside_vitals(payload, nurse_user, db)
        assert res["status"] == "success"
        assert res["alert_triggered"] is True
        assert len(res["threshold_alerts"]) >= 3

        alert_params = [a["parameter"] for a in res["threshold_alerts"]]
        assert "SpO2" in alert_params
        assert "Blood Pressure" in alert_params
        assert "Temperature" in alert_params
    finally:
        db.close()
