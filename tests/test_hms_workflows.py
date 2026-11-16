import io
import pytest
from datetime import date, timedelta
from sqlalchemy import select
from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    BedRegistry, Encounter, Patient, ProcurementInventory,
    ProcurementPurchaseOrder, PendingEHRUpdate, BillingInvoice,
    AppointmentBooking
)
from backend.app.services.agents.scheduling_agent import SchedulingAgent
from backend.app.services.agents.lab_pharmacy_agent import LabPharmacyAgent
from backend.app.services.agents.procurement_agent import ProcurementAgent
from backend.app.services.agents.billing_rcm_agent import BillingRCMAgent
from backend.app.services.agents.conversational_bi_agent import ConversationalBIAgent
from backend.app.services.doctor_verification_service import DoctorVerificationService
from backend.app.services.pdf_export_service import LongitudinalPDFExportService


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_100_bed_occupancy_and_allocation(db_session):
    overview = SchedulingAgent.get_bed_overview(db_session)

    assert overview["total_beds"] == 100
    assert "occupied_beds" in overview
    assert "available_beds" in overview
    assert overview["total_beds"] == overview["occupied_beds"] + overview["available_beds"] + overview["cleaning_beds"] + overview["maintenance_beds"]
    assert len(overview["wards"]) == 10

    # Test Bed Admission & Discharge cycle
    available_bed = SchedulingAgent.find_available_bed(ward="General Male", db=db_session)
    if available_bed:
        adm_result = SchedulingAgent.create_admission_request(
            patient_id="PAT-00001",
            department="Cardiology",
            recommended_ward="General Male",
            priority="routine",
            admission_notes="E2E test observation admission",
            doctor_id="DOC-CARD-001",
            db=db_session
        )
        assert "request_id" in adm_result
        assert adm_result["status"] in ["admitted", "assigned"]
        req_id = adm_result["request_id"]

        # Now test discharge
        disch_result = SchedulingAgent.discharge_patient(req_id, db=db_session)
        assert disch_result["status"] == "discharged"


def test_doctor_double_booking_prevention(db_session):
    booking_date = date.today() + timedelta(days=60)
    time_slot = "05:15 PM"
    doc_id = "DOC-CARD-001"

    # Clean up any residual test booking from previous runs to ensure idempotency
    existing_test_appts = db_session.scalars(
        select(AppointmentBooking).where(
            AppointmentBooking.doctor_id == doc_id,
            AppointmentBooking.booking_date == booking_date,
            AppointmentBooking.time_slot == time_slot
        )
    ).all()
    for appt in existing_test_appts:
        db_session.delete(appt)
    db_session.commit()

    # 1. First booking succeeds
    first_booking = SchedulingAgent.book_appointment(
        patient_id="PAT-00001",
        doctor_id=doc_id,
        booking_date=booking_date,
        time_slot=time_slot,
        chief_complaint="Routine cardiology follow-up",
        db=db_session
    )
    assert first_booking["status"] == "confirmed"
    assert "booking_id" in first_booking

    # 2. Second booking at exact same slot must be prevented
    with pytest.raises(ValueError) as excinfo:
        SchedulingAgent.book_appointment(
            patient_id="PAT-00002",
            doctor_id=doc_id,
            booking_date=booking_date,
            time_slot=time_slot,
            chief_complaint="Conflicting appointment",
            db=db_session
        )
    assert "already booked" in str(excinfo.value).lower()


def test_doctor_verification_workflow(db_session):
    # 1. Patient shares info via chat, staged as pending
    staged = DoctorVerificationService.stage_pending_update(
        patient_id="PAT-00001",
        update_type="condition",
        source="patient_chat",
        proposed_data={
            "condition_name": "Mild Intermittent Asthma",
            "condition_code": "J45.909",
            "onset_date": "2026-11-01"
        },
        assigned_doctor_id="DOC-CARD-001",
        db=db_session
    )
    assert staged["status"] == "pending_verification"
    update_id = staged["update_id"]

    # 2. Doctor reviews and approves the update
    reviewed = DoctorVerificationService.review_update(
        update_id=update_id,
        action="approve",
        reviewed_by="DOC-CARD-001",
        review_notes="Verified via peak flow exam",
        db=db_session
    )
    assert reviewed["status"] == "approved"
    assert reviewed["reviewed_by"] == "DOC-CARD-001"


def test_lab_pharmacy_drug_interaction(db_session):
    # Check drug safety for Aspirin on a patient with Warfarin or check known interactions
    safety_result = LabPharmacyAgent.check_drug_safety(
        proposed_medication="Aspirin 81mg",
        patient_id="PAT-00001",
        db=db_session
    )
    assert "is_safe" in safety_result
    assert "drug_interactions" in safety_result
    assert "allergy_conflicts" in safety_result


def test_procurement_audit_and_authorization(db_session):
    audit = ProcurementAgent.audit_inventory(db_session)

    assert "total_inventory_items" in audit
    assert "low_stock_items" in audit
    assert "critical_items" in audit

    # If draft purchase order exists, test authorization
    draft_po = db_session.scalar(
        select(ProcurementPurchaseOrder).where(
            ProcurementPurchaseOrder.status == "draft_pending_authorization"
        )
    )
    if draft_po:
        auth = ProcurementAgent.authorize_purchase_order(
            po_id=draft_po.po_id,
            action="approve",
            approved_by="ADMIN-EXEC-01",
            db=db_session
        )
        assert auth["status"] == "approved"


def test_billing_rcm_and_icd10_assistance(db_session):
    # Test ICD-10 assistance
    coded = BillingRCMAgent.assist_icd10_coding("Patient diagnosed with essential primary hypertension and angina")
    assert len(coded) >= 1
    codes = [c["code"] for c in coded]
    assert "I10" in codes or "I20.9" in codes

    # Test generating itemized patient invoice
    inv = BillingRCMAgent.generate_patient_invoice(
        patient_id="PAT-00001",
        items=[
            {"description": "Specialist Consultation - Cardiology", "amount": 1500.0, "category": "consultation"},
            {"description": "Electrocardiogram (ECG)", "amount": 800.0, "category": "diagnostic"}
        ],
        insurance_percentage=75.0,
        clinical_context="Cardiovascular evaluation",
        db=db_session
    )
    assert inv["invoice_id"].startswith("INV-")
    assert inv["total_amount"] == 2300.0
    assert inv["insurance_covered"] == 1725.0
    assert inv["patient_payable"] == 575.0


def test_conversational_bi_queries(db_session):
    # Query 1: Bed Occupancy
    res1 = ConversationalBIAgent.query("What is today's bed occupancy?", db_session)
    assert "100-Bed" in res1["summary"] or "Occupancy" in res1["summary"]
    assert res1["chart"]["type"] in ["bar", "donut", "pie"]

    # Query 2: Low Stock Inventory
    res2 = ConversationalBIAgent.query("Show medicines running low in inventory", db_session)
    assert "Pharmacy" in res2["summary"] or "Stock" in res2["summary"] or "Inventory" in res2["summary"]


def test_longitudinal_ehr_pdf_export(db_session):
    pdf_stream = LongitudinalPDFExportService.build_ehr_pdf("PAT-00001", db_session)
    pdf_bytes = pdf_stream.getvalue()

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 5000  # Multi-page PDF with graphics and tables
    assert pdf_bytes.startswith(b"%PDF")


def test_multi_hospital_doctors_and_appointment_ticket(db_session):
    # 1. Verify multiple doctors across multiple hospitals for Cardiology
    cardio_docs = SchedulingAgent.get_available_doctors(department="Cardiology", db=db_session)
    assert len(cardio_docs) >= 3
    hospitals = set(d["hospital_name"] for d in cardio_docs)
    assert len(hospitals) >= 2, "Cardiology must feature multiple partner hospitals"

    # 2. Book appointment and verify rich ticket metadata
    test_slot = "09:00 AM"
    target_date = date.today() + timedelta(days=90)
    target_doc = cardio_docs[0]

    # Clean residual booking if any
    old = db_session.scalar(
        select(AppointmentBooking).where(
            AppointmentBooking.doctor_id == target_doc["doctor_id"],
            AppointmentBooking.booking_date == target_date,
            AppointmentBooking.time_slot == test_slot
        )
    )
    if old:
        db_session.delete(old)
        db_session.commit()

    ticket = SchedulingAgent.book_appointment(
        patient_id="PAT-00001",
        doctor_id=target_doc["doctor_id"],
        booking_date=target_date,
        time_slot=test_slot,
        chief_complaint="Comprehensive multi-hospital ticket test",
        booked_via="intake_agent",
        db=db_session
    )

    # Verify official ticket fields
    assert "token_number" in ticket
    assert ticket["token_number"].startswith("TKT-")
    assert "chamber_room" in ticket
    assert "hospital_name" in ticket
    assert ticket["hospital_name"] == target_doc["hospital_name"]
    assert ticket["status"] == "confirmed"
    assert ticket["patient_id"] == "PAT-00001"

    # Verify booking exists as a real entity in Postgres
    saved_booking = db_session.scalar(
        select(AppointmentBooking).where(AppointmentBooking.booking_id == ticket["booking_id"])
    )
    assert saved_booking is not None
    assert saved_booking.hospital_name == target_doc["hospital_name"]


def test_matplotlib_clinical_chart_generation(db_session):
    from backend.app.services.matplotlib_chart_service import MatplotlibChartService

    # 1. Test BP Matplotlib chart generation
    bp_chart = MatplotlibChartService.generate_chart_for_patient("PAT-00001", "blood_pressure", db_session)
    assert "chart_image_base64" in bp_chart
    assert bp_chart["chart_image_base64"].startswith("data:image/png;base64,")
    assert len(bp_chart["chart_image_base64"]) > 5000  # Valid high-resolution PNG image
    assert bp_chart["metric"] == "blood_pressure"
    assert bp_chart["unit"] == "mmHg"
    assert len(bp_chart["points"]) >= 2

    # 2. Test Glucose Matplotlib chart generation
    gl_chart = MatplotlibChartService.generate_chart_for_patient("PAT-00001", "glucose", db_session)
    assert gl_chart["chart_image_base64"].startswith("data:image/png;base64,")
    assert gl_chart["metric"] == "glucose"
    assert gl_chart["unit"] == "mg/dL"


def test_educational_medical_visuals_for_concepts():
    from backend.app.services.educational_visuals_service import EducationalVisualsService

    # 1. Curated concept (MRI scan)
    mri_visual = EducationalVisualsService.find_or_resolve_visual("Explain what is an MRI scan")
    assert mri_visual is not None
    assert "image_url" in mri_visual
    assert mri_visual["image_url"].startswith("http")
    assert "Magnetic Resonance" in mri_visual["title"]
    assert "Not Patient Scan" in mri_visual["badge"]

    # 2. Curated concept (Heart Attack / Myocardial Infarction)
    mi_visual = EducationalVisualsService.find_or_resolve_visual("What is myocardial infarction?")
    assert mi_visual is not None
    assert "Myocardial Infarction" in mi_visual["title"]
    assert len(mi_visual["key_points"]) >= 2

    # 3. Dynamic lookup concept (Appendicitis)
    app_visual = EducationalVisualsService.find_or_resolve_visual("Explain appendicitis")
    assert app_visual is not None
    assert "image_url" in app_visual
    assert "Appendicitis" in app_visual["title"]


def test_genuine_future_disease_risk_service(db_session):
    from backend.app.services.clinical_future_risk_service import ClinicalFutureRiskService

    # 1. Patient PAT-00001 has diagnosed Type 2 Diabetes on file
    # Ensure the model does NOT predict incident Type 2 Diabetes for a patient who already has it!
    res1 = ClinicalFutureRiskService.evaluate_patient_future_risk(db_session, "PAT-00001")
    assert res1.patient_id == "PAT-00001"
    assert res1.target_condition != "Incident Type 2 Diabetes Mellitus"  # Removed hardcoded incident diabetes
    dm_eval1 = next(e for e in res1.condition_evaluations if e.icd10_code == "E11.9")
    assert dm_eval1.status == "PRE_EXISTING_CONDITION"
    assert dm_eval1.risk_tier == "Diagnosed"
    assert dm_eval1.risk_score == 1.0

    # 2. Patient PAT-00003 has CAD but NO glycemic observations (glucose/HbA1c)
    # Ensure the model does NOT default or force Type 2 Diabetes on anyone without labs!
    res3 = ClinicalFutureRiskService.evaluate_patient_future_risk(db_session, "PAT-00003")
    dm_eval3 = next(e for e in res3.condition_evaluations if e.icd10_code == "E11.9")
    assert dm_eval3.status == "INSUFFICIENT_BIOMARKERS"
    assert dm_eval3.risk_score is None
    assert dm_eval3.risk_tier == "Indeterminate"
    assert "Fasting Plasma Glucose & HbA1c" in res3.data_completeness.missing_biomarkers

    # 3. Patient PAT-00004 is a young healthy patient (age 24) with normal vitals and labs
    # Ensure genuine prediction yields Optimal / Low Risk across all domains
    res4 = ClinicalFutureRiskService.evaluate_patient_future_risk(db_session, "PAT-00004")
    assert res4.status == "OPTIMAL_HEALTH_PROFILE"
    assert res4.risk_category == "Low"
    assert res4.estimated_risk_score < 0.15
    for c in res4.condition_evaluations:
        assert c.risk_tier in ["Low", "Optimal"]

    # 4. Biomarker audit trail contains real measurements without synthetic fallbacks
    assert "mean_systolic_bp" in res1.historical_metrics_analyzed
    assert "total_observations_recorded" in res1.historical_metrics_analyzed
    assert res1.data_completeness.completeness_percentage > 0



