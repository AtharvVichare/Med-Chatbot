import json
import uuid
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from backend.app.db.session import get_db
from backend.app.db.models import (
    Patient,
    Encounter,
    Condition,
    Observation,
    Medication,
    Allergy,
    FamilyMember,
    FamilyCondition,
    DailyHealthLog,
    PatientDocument,
    BedRegistry,
    AdmissionRequest,
    AppointmentBooking,
    DoctorProfile,
    PendingEHRUpdate,
    ClinicalNote,
    ClinicalOrder,
    CareTeamAssignment,
    AuditLog
)
from backend.app.db.schemas import (
    ClinicalNoteCreate,
    ClinicalNoteRead,
    ClinicalOrderCreate,
    ClinicalOrderRead,
)
from backend.app.core.dependencies import get_current_user, log_audit_event
from backend.app.core.demo_users import User
from backend.app.services.ehr_service import LongitudinalEHRService
from backend.app.services.agents.lab_pharmacy_agent import LabPharmacyAgent

router = APIRouter(prefix="/doctor", tags=["Doctor Clinical Workspace"])


@router.get("/overview")
def get_doctor_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Doctor Overview: Real-time clinical summary including today's appointments,
    assigned inpatients, pending verifications, pending orders, and critical patient alerts.
    """
    if current_user.role == "doctor":
        doctor_name = current_user.full_name or "Dr. Priya Deshmukh"
    else:
        doctor_name = "Dr. Priya Deshmukh"
    today = date.today()

    # 1. Today's Appointments
    appointments_query = db.query(AppointmentBooking).filter(
        AppointmentBooking.booking_date == today
    )
    todays_appointments = appointments_query.order_by(AppointmentBooking.time_slot.asc()).all()

    # Enrich appointments
    appointment_list = []
    patient_ids_set = set()
    for appt in todays_appointments:
        patient = db.query(Patient).filter(Patient.patient_id == appt.patient_id).first()
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else appt.patient_id
        patient_ids_set.add(appt.patient_id)
        appointment_list.append({
            "booking_id": appt.booking_id,
            "patient_id": appt.patient_id,
            "patient_name": patient_name,
            "time_slot": appt.time_slot,
            "department": appt.department,
            "hospital_name": appt.hospital_name,
            "status": appt.status,
            "chief_complaint": appt.chief_complaint,
            "booked_via": appt.booked_via
        })

    # 2. Currently Admitted Inpatients
    admitted_requests = db.query(AdmissionRequest).filter(
        AdmissionRequest.status.in_(["assigned", "admitted"])
    ).all()

    inpatient_list = []
    for adm in admitted_requests:
        p = db.query(Patient).filter(Patient.patient_id == adm.patient_id).first()
        bed = db.query(BedRegistry).filter(BedRegistry.bed_id == adm.assigned_bed_id).first() if adm.assigned_bed_id else None
        p_name = f"{p.first_name} {p.last_name}" if p else adm.patient_id
        patient_ids_set.add(adm.patient_id)
        inpatient_list.append({
            "request_id": adm.request_id,
            "patient_id": adm.patient_id,
            "patient_name": p_name,
            "department": adm.department,
            "ward": bed.ward if bed else adm.recommended_ward,
            "bed_number": bed.bed_number if bed else "TBD",
            "priority": adm.priority,
            "admission_notes": adm.admission_notes,
            "admitted_since": adm.created_at.strftime("%Y-%m-%d %H:%M")
        })

    # 3. Pending EHR Verifications
    pending_verifications = db.query(PendingEHRUpdate).filter(
        PendingEHRUpdate.status == "pending_verification"
    ).all()

    # 4. Pending Lab / Imaging Orders
    pending_orders = db.query(ClinicalOrder).filter(
        ClinicalOrder.status.in_(["ordered", "sample_collected", "in_progress"])
    ).all()

    # 5. Critical Clinical Alerts (Evaluated from recent vitals & lab observations)
    critical_alerts = []
    recent_logs = db.query(DailyHealthLog).order_by(DailyHealthLog.log_date.desc()).limit(30).all()
    for log in recent_logs:
        p = db.query(Patient).filter(Patient.patient_id == log.patient_id).first()
        p_name = f"{p.first_name} {p.last_name}" if p else log.patient_id

        if log.spo2 and log.spo2 < 92:
            critical_alerts.append({
                "patient_id": log.patient_id,
                "patient_name": p_name,
                "alert_type": "HYPOXEMIA",
                "severity": "CRITICAL",
                "message": f"Low SpO2: {log.spo2}% on {log.log_date}",
                "timestamp": str(log.log_date)
            })
        if log.systolic_bp and (log.systolic_bp >= 160 or log.systolic_bp <= 90):
            critical_alerts.append({
                "patient_id": log.patient_id,
                "patient_name": p_name,
                "alert_type": "HYPERTENSIVE_CRISIS" if log.systolic_bp >= 160 else "HYPOTENSION",
                "severity": "URGENT",
                "message": f"Blood Pressure Alert: {log.systolic_bp}/{log.diastolic_bp} mmHg on {log.log_date}",
                "timestamp": str(log.log_date)
            })

    # 6. Upcoming Rounds and Procedures
    upcoming_rounds = [
        {"time": "09:30 AM", "type": "Morning ICU & CCU Clinical Rounds", "location": "ICU & CCU Wards"},
        {"time": "11:00 AM", "type": "OPD Consultations Block 1", "location": "Chamber 104, OPD Block B"},
        {"time": "02:30 PM", "type": "Inpatient Multi-Disciplinary Case Review", "location": "Conference Room A"},
        {"time": "04:30 PM", "type": "Evening Post-Op Rounds & Discharges", "location": "Post-Op Surgical Ward"}
    ]

    log_audit_event(db, current_user, "DOCTOR_OVERVIEW_ACCESSED", "OVERVIEW")

    return {
        "doctor_name": doctor_name,
        "specialty": "Cardiology & Internal Medicine",
        "hospital": current_user.facility or "Seth GS Medical College & KEM Hospital",
        "stats": {
            "today_appointments_count": len(appointment_list),
            "admitted_inpatients_count": len(inpatient_list),
            "pending_verifications_count": len(pending_verifications),
            "pending_orders_count": len(pending_orders),
            "critical_alerts_count": len(critical_alerts)
        },
        "today_appointments": appointment_list,
        "admitted_inpatients": inpatient_list,
        "critical_alerts": critical_alerts[:6],
        "upcoming_rounds": upcoming_rounds
    }


@router.get("/patients")
def get_doctor_patient_directory(
    status_filter: str = Query("all", description="all, admitted, outpatient, critical, new, discharged, followup"),
    search: Optional[str] = Query(None, description="Search by name or patient ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Searchable Patient Directory for Doctors.
    Provides complete clinical status, bed assignment, last consultation, and medical alerts.
    """
    query = db.query(Patient)

    if search:
        s = search.strip()
        query = query.filter(
            or_(
                Patient.patient_id.ilike(f"%{s}%"),
                Patient.first_name.ilike(f"%{s}%"),
                Patient.last_name.ilike(f"%{s}%")
            )
        )

    # Sort priority patients (e.g. Aarav Mehta and active cases) first
    patients = query.order_by(Patient.registered_date.desc()).limit(50).all()

    # Pre-fetch admissions and beds
    admissions_map = {}
    for adm in db.query(AdmissionRequest).filter(AdmissionRequest.status.in_(["assigned", "admitted"])).all():
        admissions_map[adm.patient_id] = adm

    beds_map = {b.bed_id: b for b in db.query(BedRegistry).all()}

    results = []
    for p in patients:
        adm = admissions_map.get(p.patient_id)
        bed = beds_map.get(adm.assigned_bed_id) if adm else None

        # Check latest encounter
        latest_enc = db.query(Encounter).filter(Encounter.patient_id == p.patient_id).order_by(Encounter.encounter_date.desc()).first()

        # Check next appointment
        next_appt = db.query(AppointmentBooking).filter(
            AppointmentBooking.patient_id == p.patient_id,
            AppointmentBooking.booking_date >= date.today()
        ).order_by(AppointmentBooking.booking_date.asc()).first()

        # Check active conditions
        active_conditions = db.query(Condition).filter(
            Condition.patient_id == p.patient_id,
            Condition.clinical_status == "active"
        ).all()
        condition_names = [c.diagnosis_name for c in active_conditions if c.diagnosis_name]

        # Clinical status determination
        is_admitted = adm is not None
        status_label = "Inpatient" if is_admitted else "Outpatient"
        if adm and adm.priority == "emergency":
            status_label = "Critical Care"

        # Filter check
        if status_filter == "admitted" and not is_admitted:
            continue
        if status_filter == "outpatient" and is_admitted:
            continue
        if status_filter == "critical" and (not adm or adm.priority not in ["urgent", "emergency"]):
            continue

        results.append({
            "patient_id": p.patient_id,
            "full_name": f"{p.first_name} {p.last_name}".strip(),
            "age": p.age,
            "gender": p.sex,
            "district": p.district,
            "clinical_status": status_label,
            "is_admitted": is_admitted,
            "ward": bed.ward if bed else (adm.recommended_ward if adm else "N/A"),
            "bed_number": bed.bed_number if bed else "N/A",
            "attending_doctor": latest_enc.attending_provider if latest_enc else "Dr. Priya Deshmukh",
            "department": adm.department if adm else (latest_enc.facility if latest_enc else "General Medicine"),
            "active_diagnoses": condition_names[:3],
            "last_consultation": str(latest_enc.encounter_date) if latest_enc else str(p.registered_date),
            "next_appointment": f"{next_appt.booking_date} ({next_appt.time_slot})" if next_appt else "None scheduled",
            "critical_alert": (adm and adm.priority in ["urgent", "emergency"]) or ("Asthma" in "".join(condition_names))
        })

    return results


@router.get("/patients/{patient_id}/full-ehr")
def get_patient_full_ehr_for_doctor(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dedicated Longitudinal EHR for Doctors:
    Includes Demographics, History, Diagnoses, Clinical Notes, Prescriptions,
    Allergies & Drug Interaction Warnings, Lab Observations, Scans & Images,
    Vitals Graphs, Admissions History, and Pending Verifications.
    """
    ehr = LongitudinalEHRService.get_complete_patient_record(patient_id, db)
    if "error" in ehr:
        raise HTTPException(status_code=404, detail="Patient record not found.")

    # Fetch Clinical Notes written by physicians
    clinical_notes = db.query(ClinicalNote).filter(
        ClinicalNote.patient_id == patient_id
    ).order_by(ClinicalNote.created_at.desc()).all()

    # Fetch Clinical Orders
    clinical_orders = db.query(ClinicalOrder).filter(
        ClinicalOrder.patient_id == patient_id
    ).order_by(ClinicalOrder.ordered_at.desc()).all()

    # Fetch Admission History
    admissions = db.query(AdmissionRequest).filter(
        AdmissionRequest.patient_id == patient_id
    ).order_by(AdmissionRequest.created_at.desc()).all()

    # Fetch Pending Patient Submissions
    pending_updates = db.query(PendingEHRUpdate).filter(
        PendingEHRUpdate.patient_id == patient_id,
        PendingEHRUpdate.status == "pending_verification"
    ).all()

    # Evaluate Active Drug-Drug & Drug-Allergy Interactions
    active_meds = [m.get("medication_name") for m in ehr.get("medications", []) if m.get("medication_name")]
    interaction_warnings = []
    if len(active_meds) >= 2:
        for i in range(len(active_meds)):
            for j in range(i + 1, len(active_meds)):
                safety = LabPharmacyAgent.check_drug_interactions(active_meds[i], active_meds[j])
                if safety.get("interaction_found"):
                    interaction_warnings.append({
                        "drug_a": active_meds[i],
                        "drug_b": active_meds[j],
                        "severity": safety.get("severity"),
                        "clinical_effect": safety.get("clinical_effect"),
                        "recommendation": safety.get("recommendation")
                    })

    # Medical Scans & Imaging Catalog
    imaging_scans = []
    for doc in ehr.get("documents", []):
        fn = doc.get("file_name", "").lower()
        if any(ext in fn for ext in ["xray", "x-ray", "mri", "ct", "scan", "chest", "radiology"]) or doc.get("document_type") == "radiology_scan":
            imaging_scans.append(doc)

    log_audit_event(db, current_user, "DOCTOR_FULL_EHR_ACCESSED", patient_id)

    return {
        "patient_id": patient_id,
        "demographics": ehr.get("demographics", {}),
        "conditions": ehr.get("conditions", []),
        "medications": ehr.get("medications", []),
        "allergies": ehr.get("allergies", []),
        "drug_interactions": interaction_warnings,
        "observations": ehr.get("observations", []),
        "documents": ehr.get("documents", []),
        "imaging_scans": imaging_scans,
        "encounters": ehr.get("encounters", []),
        "daily_vitals_trends": ehr.get("daily_logs", []),
        "family_history": ehr.get("family_history", []),
        "clinical_notes": [
            {
                "note_id": n.note_id,
                "note_type": n.note_type,
                "title": n.title,
                "doctor_name": n.doctor_name,
                "content": n.content,
                "subjective": n.subjective,
                "objective": n.objective,
                "assessment": n.assessment,
                "plan": n.plan,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
            } for n in clinical_notes
        ],
        "clinical_orders": [
            {
                "order_id": o.order_id,
                "order_type": o.order_type,
                "order_name": o.order_name,
                "priority": o.priority,
                "status": o.status,
                "clinical_indication": o.clinical_indication,
                "ordered_at": o.ordered_at.strftime("%Y-%m-%d %H:%M"),
                "result_summary": o.result_summary
            } for o in clinical_orders
        ],
        "admissions_history": [
            {
                "request_id": a.request_id,
                "department": a.department,
                "ward": a.recommended_ward,
                "priority": a.priority,
                "status": a.status,
                "notes": a.admission_notes,
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M")
            } for a in admissions
        ],
        "pending_verifications": [
            {
                "update_id": u.update_id,
                "update_type": u.update_type,
                "source": u.source,
                "proposed_data": json.loads(u.proposed_data) if u.proposed_data else {},
                "created_at": u.created_at.strftime("%Y-%m-%d %H:%M")
            } for u in pending_updates
        ]
    }


@router.post("/clinical-notes", response_model=ClinicalNoteRead, status_code=status.HTTP_201_CREATED)
def create_clinical_note(
    payload: ClinicalNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Physician Clinical Documentation:
    Create consultation notes, SOAP notes, discharge summaries, treatment plans, or referrals.
    """
    if current_user.role == "doctor":
        doctor_name = current_user.full_name or "Dr. Priya Deshmukh"
        doctor_id = current_user.username
    else:
        doctor_name = "Dr. Priya Deshmukh"
        doctor_id = "DOC-CARD-001"
    note_id = f"NOTE-{uuid.uuid4().hex[:10].upper()}"

    note = ClinicalNote(
        note_id=note_id,
        patient_id=payload.patient_id,
        encounter_id=payload.encounter_id,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        note_type=payload.note_type,
        title=payload.title,
        subjective=payload.subjective,
        objective=payload.objective,
        assessment=payload.assessment,
        plan=payload.plan,
        content=payload.content,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    p = db.query(Patient).filter(Patient.patient_id == payload.patient_id).first()
    log_audit_event(db, current_user, "CLINICAL_NOTE_CREATED", note_id, f"Type: {payload.note_type}")

    return ClinicalNoteRead(
        note_id=note.note_id,
        patient_id=note.patient_id,
        patient_name=f"{p.first_name} {p.last_name}" if p else note.patient_id,
        encounter_id=note.encounter_id,
        doctor_id=note.doctor_id,
        doctor_name=note.doctor_name,
        note_type=note.note_type,
        title=note.title,
        subjective=note.subjective,
        objective=note.objective,
        assessment=note.assessment,
        plan=note.plan,
        content=note.content,
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat()
    )


@router.post("/orders", response_model=ClinicalOrderRead, status_code=status.HTTP_201_CREATED)
def create_clinical_order(
    payload: ClinicalOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Order diagnostic investigations (Lab, Imaging - X-Ray, CT, MRI, Procedure).
    """
    if current_user.role == "doctor":
        doctor_name = current_user.full_name or "Dr. Priya Deshmukh"
        doctor_id = current_user.username
    else:
        doctor_name = "Dr. Priya Deshmukh"
        doctor_id = "DOC-CARD-001"
    order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"

    order = ClinicalOrder(
        order_id=order_id,
        patient_id=payload.patient_id,
        encounter_id=payload.encounter_id,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        order_type=payload.order_type,
        order_name=payload.order_name,
        clinical_indication=payload.clinical_indication,
        priority=payload.priority,
        status="ordered",
        ordered_at=datetime.now(timezone.utc)
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    p = db.query(Patient).filter(Patient.patient_id == payload.patient_id).first()
    log_audit_event(db, current_user, "CLINICAL_ORDER_CREATED", order_id, f"{payload.order_type}: {payload.order_name}")

    return ClinicalOrderRead(
        order_id=order.order_id,
        patient_id=order.patient_id,
        patient_name=f"{p.first_name} {p.last_name}" if p else order.patient_id,
        encounter_id=order.encounter_id,
        doctor_id=order.doctor_id,
        doctor_name=order.doctor_name,
        order_type=order.order_type,
        order_name=order.order_name,
        clinical_indication=order.clinical_indication,
        priority=order.priority,
        status=order.status,
        result_summary=order.result_summary,
        ordered_at=order.ordered_at.isoformat(),
        completed_at=None
    )


@router.post("/copilot/draft-note")
def generate_ai_copilot_draft_note(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI Clinical Copilot: Synthesizes patient longitudinal EHR into a draft SOAP note,
    consultation summary, or discharge summary. Marked as DRAFT until physician review & approval.
    """
    patient_id = payload.get("patient_id")
    note_type = payload.get("note_type", "soap_note")
    clinical_focus = payload.get("clinical_focus", "Routine consultation follow-up")

    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required.")

    p = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found.")

    conditions = db.query(Condition).filter(Condition.patient_id == patient_id).all()
    cond_str = ", ".join([c.diagnosis_name for c in conditions if c.diagnosis_name]) or "None documented"

    meds = db.query(Medication).filter(Medication.patient_id == patient_id, Medication.status == "active").all()
    meds_str = ", ".join([f"{m.medication_name} ({m.dosage})" for m in meds if m.medication_name]) or "None active"

    allergies = db.query(Allergy).filter(Allergy.patient_id == patient_id).all()
    allergy_str = ", ".join([f"{a.substance} ({a.reaction})" for a in allergies]) or "NKDA (No Known Drug Allergies)"

    latest_vitals = db.query(DailyHealthLog).filter(DailyHealthLog.patient_id == patient_id).order_by(DailyHealthLog.log_date.desc()).first()
    vitals_str = f"BP: {latest_vitals.systolic_bp}/{latest_vitals.diastolic_bp} mmHg, Pulse: {latest_vitals.pulse} bpm, SpO2: {latest_vitals.spo2}%" if latest_vitals else "Vitals pending intake recording"

    draft = {
        "patient_id": patient_id,
        "patient_name": f"{p.first_name} {p.last_name}",
        "draft_status": "DRAFT - Requires Attending Physician Review & Signature",
        "generated_by": "Aarogya Clinical AI Copilot",
        "title": f"Consultation Follow-Up: {clinical_focus}",
        "subjective": f"Patient {p.first_name} {p.last_name}, {p.age}yo {p.sex}, presents for evaluation regarding {clinical_focus}. Historical diagnoses include {cond_str}. Patient reports adherence to current prescribed regimen: {meds_str}. No new adverse reactions reported.",
        "objective": f"Vital Signs: {vitals_str}. Known Allergies: {allergy_str}. Physical examination unremarkable for acute distress. Auscultation clear bilaterally, regular rate and rhythm.",
        "assessment": f"1. {cond_str}. Stable on present therapy without acute clinical exacerbation.\n2. Preventive wellness and monitoring follow-up.",
        "plan": f"1. Continue present medication regimen: {meds_str}.\n2. Maintain ambulatory vitals tracking (BP, SpO2, Heart Rate).\n3. Re-check complete metabolic panel in 90 days.\n4. Strict allergy avoidance ({allergy_str}).\n5. Follow-up consultation in 4 weeks or SOS if red-flag symptoms arise.",
        "suggested_investigations": [
            "Complete Blood Count (CBC) with differential",
            "Comprehensive Metabolic Panel (CMP)",
            "12-Lead Electrocardiogram (ECG) if palpitations develop"
        ]
    }

    log_audit_event(db, current_user, "COPILOT_DRAFT_GENERATED", patient_id)
    return draft
