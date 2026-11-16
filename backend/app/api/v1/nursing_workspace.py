import json
import uuid
from datetime import datetime, date, timezone, timedelta
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
    DailyHealthLog,
    BedRegistry,
    AdmissionRequest,
    AppointmentBooking,
    NursingTask,
    MedicationAdministration,
    ShiftHandover,
    ClinicalOrder,
    CareTeamAssignment,
    AuditLog
)
from backend.app.db.schemas import (
    NursingTaskCreate,
    NursingTaskUpdate,
    NursingTaskRead,
    MedicationAdministrationCreate,
    MedicationAdministrationRecordAction,
    MedicationAdministrationRead,
    ShiftHandoverCreate,
    ShiftHandoverRead,
)
from backend.app.core.dependencies import get_current_user, log_audit_event
from backend.app.core.demo_users import User

router = APIRouter(prefix="/nurse", tags=["Nurse Patient Care Workspace"])


def get_current_shift_info():
    """Determine current active nursing shift based on local hour."""
    now = datetime.now()
    hour = now.hour
    if 7 <= hour < 15:
        return {"shift_type": "morning", "label": "Morning Shift (07:00 - 15:00)", "active": True}
    elif 15 <= hour < 23:
        return {"shift_type": "evening", "label": "Evening Shift (15:00 - 23:00)", "active": True}
    else:
        return {"shift_type": "night", "label": "Night Shift (23:00 - 07:00)", "active": True}


@router.get("/overview")
def get_nurse_overview(
    ward_filter: Optional[str] = Query(None, description="Optional ward filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Nurse Overview: Active shift details, assigned ward stats, occupied beds,
    immediate attention alerts, pending MAR medication doses, and overdue tasks.
    """
    if current_user.role == "nurse":
        nurse_name = current_user.full_name or "Nurse Anjali Sharma"
    else:
        nurse_name = "Nurse Anjali Sharma"
    shift_info = get_current_shift_info()
    target_ward = ward_filter or "ICU"

    # Bed statistics
    total_beds = db.query(BedRegistry).count()
    occupied_beds = db.query(BedRegistry).filter(BedRegistry.is_occupied == True).count()
    available_beds = total_beds - occupied_beds

    # Active admissions in facility
    active_admissions = db.query(AdmissionRequest).filter(
        AdmissionRequest.status.in_(["assigned", "admitted"])
    ).all()

    # Pending Medication Administrations (MAR)
    pending_mar = db.query(MedicationAdministration).filter(
        MedicationAdministration.status == "scheduled"
    ).order_by(MedicationAdministration.scheduled_time.asc()).limit(15).all()

    mar_list = []
    for m in pending_mar:
        p = db.query(Patient).filter(Patient.patient_id == m.patient_id).first()
        mar_list.append({
            "mar_id": m.mar_id,
            "patient_id": m.patient_id,
            "patient_name": f"{p.first_name} {p.last_name}" if p else m.patient_id,
            "medication_name": m.medication_name,
            "dosage": m.dosage,
            "route": m.route,
            "scheduled_time": m.scheduled_time.strftime("%H:%M"),
            "status": m.status
        })

    # Pending Nursing Tasks
    pending_tasks = db.query(NursingTask).filter(
        NursingTask.status.in_(["pending", "in_progress", "overdue"])
    ).order_by(NursingTask.scheduled_time.asc()).limit(15).all()

    task_list = []
    now_utc = datetime.now(timezone.utc)
    for t in pending_tasks:
        p = db.query(Patient).filter(Patient.patient_id == t.patient_id).first()
        is_overdue = t.scheduled_time.replace(tzinfo=timezone.utc) < now_utc if t.scheduled_time.tzinfo is None else t.scheduled_time < now_utc
        task_list.append({
            "task_id": t.task_id,
            "patient_id": t.patient_id,
            "patient_name": f"{p.first_name} {p.last_name}" if p else t.patient_id,
            "ward": t.ward,
            "bed_number": t.bed_number,
            "task_type": t.task_type,
            "title": t.title,
            "priority": t.priority,
            "scheduled_time": t.scheduled_time.strftime("%H:%M"),
            "status": "overdue" if (is_overdue and t.status == "pending") else t.status
        })

    # Immediate Attention Alerts (Clinical Vital Threshold breaches)
    immediate_attention = []
    recent_logs = db.query(DailyHealthLog).order_by(DailyHealthLog.log_date.desc()).limit(20).all()
    for log in recent_logs:
        p = db.query(Patient).filter(Patient.patient_id == log.patient_id).first()
        p_name = f"{p.first_name} {p.last_name}" if p else log.patient_id

        # Low SpO2 threshold < 92%
        if log.spo2 and log.spo2 < 92:
            immediate_attention.append({
                "patient_id": log.patient_id,
                "patient_name": p_name,
                "type": "CRITICAL_SPO2",
                "severity": "CRITICAL",
                "message": f"Desaturation: SpO2 {log.spo2}% (Normal > 95%). Prompt oxygen titration advised.",
                "recorded_at": str(log.log_date)
            })

        # Severe Hypertension > 160 mmHg or Hypotension < 90 mmHg
        if log.systolic_bp and (log.systolic_bp >= 160 or log.systolic_bp <= 90):
            immediate_attention.append({
                "patient_id": log.patient_id,
                "patient_name": p_name,
                "type": "BLOOD_PRESSURE_ALERT",
                "severity": "URGENT",
                "message": f"Abnormal BP: {log.systolic_bp}/{log.diastolic_bp} mmHg. Re-check and notify attending.",
                "recorded_at": str(log.log_date)
            })

    log_audit_event(db, current_user, "NURSE_OVERVIEW_ACCESSED", "NURSE_STATION")

    return {
        "nurse_name": nurse_name,
        "shift": shift_info,
        "assigned_ward": target_ward,
        "hospital": current_user.facility or "Seth GS Medical College & KEM Hospital",
        "stats": {
            "total_facility_beds": total_beds,
            "occupied_beds": occupied_beds,
            "available_beds": available_beds,
            "active_inpatients_count": len(active_admissions),
            "pending_mar_count": len(mar_list),
            "pending_tasks_count": len(task_list),
            "immediate_attention_count": len(immediate_attention)
        },
        "immediate_attention": immediate_attention[:5],
        "pending_mar_doses": mar_list,
        "nursing_tasks": task_list
    }


@router.get("/bed-board")
def get_nurse_bed_board(
    ward: Optional[str] = Query(None, description="Ward filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Real-time Bed Board for Nurses:
    Bed number, ward, category, occupancy status, patient assigned, attending doctor,
    assigned nurse, and admission details.
    """
    query = db.query(BedRegistry)
    if ward and ward.lower() != "all":
        query = query.filter(BedRegistry.ward.ilike(f"%{ward}%"))

    beds = query.order_by(BedRegistry.ward.asc(), BedRegistry.bed_number.asc()).all()

    # Pre-map patients and admissions
    admissions_map = {adm.assigned_bed_id: adm for adm in db.query(AdmissionRequest).filter(AdmissionRequest.status.in_(["assigned", "admitted"])).all()}
    patients_map = {p.patient_id: p for p in db.query(Patient).all()}

    output = []
    for b in beds:
        adm = admissions_map.get(b.bed_id)
        p_id = b.current_patient_id or (adm.patient_id if adm else None)
        p = patients_map.get(p_id) if p_id else None

        output.append({
            "bed_id": b.bed_id,
            "bed_number": b.bed_number,
            "ward": b.ward,
            "bed_type": b.bed_type,
            "status": b.status,
            "is_occupied": b.is_occupied or (p_id is not None),
            "daily_charge": b.daily_charge,
            "patient_id": p_id,
            "patient_name": f"{p.first_name} {p.last_name}" if p else ("Occupied" if b.is_occupied else None),
            "patient_age_sex": f"{p.age}y/{p.sex}" if p else None,
            "attending_doctor": adm.doctor_id if (adm and adm.doctor_id) else "Dr. Priya Deshmukh",
            "assigned_nurse": "Nurse Anjali Sharma",
            "admission_date": adm.created_at.strftime("%Y-%m-%d %H:%M") if adm else None,
            "priority": adm.priority if adm else "routine",
            "notes": b.notes
        })

    return output


@router.get("/tasks")
def list_nursing_tasks(
    ward: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List nursing tasks with flexible ward and status filters.
    """
    query = db.query(NursingTask)
    if ward and ward.lower() != "all":
        query = query.filter(NursingTask.ward.ilike(f"%{ward}%"))
    if status_filter:
        query = query.filter(NursingTask.status == status_filter)
    if priority:
        query = query.filter(NursingTask.priority == priority)

    tasks = query.order_by(NursingTask.scheduled_time.asc()).all()

    # Preload patient names
    patients = {p.patient_id: f"{p.first_name} {p.last_name}" for p in db.query(Patient).all()}

    output = []
    for t in tasks:
        output.append(NursingTaskRead(
            task_id=t.task_id,
            patient_id=t.patient_id,
            patient_name=patients.get(t.patient_id, t.patient_id),
            encounter_id=t.encounter_id,
            ward=t.ward,
            bed_number=t.bed_number,
            task_type=t.task_type,
            title=t.title,
            description=t.description,
            priority=t.priority,
            scheduled_time=t.scheduled_time.isoformat(),
            status=t.status,
            assigned_nurse_id=t.assigned_nurse_id,
            assigned_nurse_name=t.assigned_nurse_name,
            completed_at=t.completed_at.isoformat() if t.completed_at else None,
            completed_by=t.completed_by,
            completion_notes=t.completion_notes,
            created_at=t.created_at.isoformat()
        ))
    return output


@router.post("/tasks", response_model=NursingTaskRead, status_code=status.HTTP_201_CREATED)
def create_nursing_task(
    payload: NursingTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new nursing task (medication round, vitals recording, lab sample collection, etc.).
    """
    task_id = f"TSK-{uuid.uuid4().hex[:10].upper()}"
    if current_user.role == "nurse":
        nurse_name = current_user.full_name or "Nurse Anjali Sharma"
    else:
        nurse_name = "Nurse Anjali Sharma"

    task = NursingTask(
        task_id=task_id,
        patient_id=payload.patient_id,
        encounter_id=payload.encounter_id,
        ward=payload.ward,
        bed_number=payload.bed_number,
        task_type=payload.task_type,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        scheduled_time=payload.scheduled_time,
        status="pending",
        assigned_nurse_id=payload.assigned_nurse_id or current_user.username,
        assigned_nurse_name=payload.assigned_nurse_name or nurse_name,
        created_at=datetime.now(timezone.utc)
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    p = db.query(Patient).filter(Patient.patient_id == payload.patient_id).first()
    log_audit_event(db, current_user, "NURSING_TASK_CREATED", task_id, payload.title)

    return NursingTaskRead(
        task_id=task.task_id,
        patient_id=task.patient_id,
        patient_name=f"{p.first_name} {p.last_name}" if p else task.patient_id,
        encounter_id=task.encounter_id,
        ward=task.ward,
        bed_number=task.bed_number,
        task_type=task.task_type,
        title=task.title,
        description=task.description,
        priority=task.priority,
        scheduled_time=task.scheduled_time.isoformat(),
        status=task.status,
        assigned_nurse_id=task.assigned_nurse_id,
        assigned_nurse_name=task.assigned_nurse_name,
        completed_at=None,
        completed_by=None,
        completion_notes=None,
        created_at=task.created_at.isoformat()
    )


@router.patch("/tasks/{task_id}", response_model=NursingTaskRead)
def update_nursing_task_status(
    task_id: str,
    payload: NursingTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update nursing task status (in_progress, completed, overdue, cancelled) with notes.
    """
    task = db.query(NursingTask).filter(NursingTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Nursing task not found.")

    if payload.status:
        task.status = payload.status
        if payload.status == "completed":
            task.completed_at = datetime.now(timezone.utc)
            task.completed_by = current_user.full_name or "Nurse Anjali Sharma"

    if payload.completion_notes:
        task.completion_notes = payload.completion_notes
    if payload.assigned_nurse_id:
        task.assigned_nurse_id = payload.assigned_nurse_id
    if payload.assigned_nurse_name:
        task.assigned_nurse_name = payload.assigned_nurse_name

    db.commit()
    db.refresh(task)

    p = db.query(Patient).filter(Patient.patient_id == task.patient_id).first()
    log_audit_event(db, current_user, "NURSING_TASK_UPDATED", task_id, f"Status: {task.status}")

    return NursingTaskRead(
        task_id=task.task_id,
        patient_id=task.patient_id,
        patient_name=f"{p.first_name} {p.last_name}" if p else task.patient_id,
        encounter_id=task.encounter_id,
        ward=task.ward,
        bed_number=task.bed_number,
        task_type=task.task_type,
        title=task.title,
        description=task.description,
        priority=task.priority,
        scheduled_time=task.scheduled_time.isoformat(),
        status=task.status,
        assigned_nurse_id=task.assigned_nurse_id,
        assigned_nurse_name=task.assigned_nurse_name,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        completed_by=task.completed_by,
        completion_notes=task.completion_notes,
        created_at=task.created_at.isoformat()
    )


@router.get("/mar")
def list_medication_administration_records(
    patient_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Medication Administration Records (MAR):
    Shows scheduled, administered, delayed, refused, or missed medications with safety checks.
    """
    query = db.query(MedicationAdministration)
    if patient_id:
        query = query.filter(MedicationAdministration.patient_id == patient_id)
    if status_filter:
        query = query.filter(MedicationAdministration.status == status_filter)

    records = query.order_by(MedicationAdministration.scheduled_time.desc()).all()
    patients = {p.patient_id: f"{p.first_name} {p.last_name}" for p in db.query(Patient).all()}

    output = []
    for r in records:
        output.append(MedicationAdministrationRead(
            mar_id=r.mar_id,
            patient_id=r.patient_id,
            patient_name=patients.get(r.patient_id, r.patient_id),
            medication_id=r.medication_id,
            medication_name=r.medication_name,
            dosage=r.dosage,
            route=r.route,
            scheduled_time=r.scheduled_time.isoformat(),
            administered_time=r.administered_time.isoformat() if r.administered_time else None,
            administered_by=r.administered_by,
            status=r.status,
            reason=r.reason,
            notes=r.notes,
            created_at=r.created_at.isoformat()
        ))
    return output


@router.post("/mar/{mar_id}/administer", response_model=MedicationAdministrationRead)
def administer_medication_record(
    mar_id: str,
    payload: MedicationAdministrationRecordAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record medication administration action (administered, delayed, refused, missed).
    Requires nurse attribution and mandatory reason if not administered on schedule.
    """
    mar = db.query(MedicationAdministration).filter(MedicationAdministration.mar_id == mar_id).first()
    if not mar:
        raise HTTPException(status_code=404, detail="MAR record not found.")

    if payload.status not in ["administered", "delayed", "refused", "missed"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be administered, delayed, refused, or missed.")

    if payload.status in ["delayed", "refused", "missed"] and not payload.reason:
        raise HTTPException(status_code=400, detail="A clinical justification reason is required when medication is delayed, refused, or missed.")

    mar.status = payload.status
    mar.administered_time = datetime.now(timezone.utc)
    mar.administered_by = current_user.full_name or "Nurse Anjali Sharma"
    mar.reason = payload.reason
    if payload.notes:
        mar.notes = payload.notes

    db.commit()
    db.refresh(mar)

    p = db.query(Patient).filter(Patient.patient_id == mar.patient_id).first()
    log_audit_event(db, current_user, "MEDICATION_ADMINISTRATION_LOGGED", mar_id, f"Drug: {mar.medication_name}, Status: {payload.status}")

    return MedicationAdministrationRead(
        mar_id=mar.mar_id,
        patient_id=mar.patient_id,
        patient_name=f"{p.first_name} {p.last_name}" if p else mar.patient_id,
        medication_id=mar.medication_id,
        medication_name=mar.medication_name,
        dosage=mar.dosage,
        route=mar.route,
        scheduled_time=mar.scheduled_time.isoformat(),
        administered_time=mar.administered_time.isoformat() if mar.administered_time else None,
        administered_by=mar.administered_by,
        status=mar.status,
        reason=mar.reason,
        notes=mar.notes,
        created_at=mar.created_at.isoformat()
    )


@router.post("/vitals")
def record_nurse_bedside_vitals(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record bedside vitals by nurse with automatic Clinical Threshold Alert Evaluation.
    Evaluates: SpO2 < 92%, Systolic BP > 160 or < 90, Heart Rate > 110 or < 50, Temp > 38.5C.
    """
    patient_id = payload.get("patient_id")
    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required.")

    systolic = payload.get("systolic_bp")
    diastolic = payload.get("diastolic_bp")
    pulse = payload.get("pulse")
    spo2 = payload.get("spo2")
    temperature_c = payload.get("temperature_c")
    fasting_glucose = payload.get("fasting_glucose")
    notes = payload.get("notes")

    # Record in DailyHealthLog
    log_entry = DailyHealthLog(
        id=f"VTL-{uuid.uuid4().hex[:10].upper()}",
        patient_id=patient_id,
        log_date=date.today(),
        systolic_bp=float(systolic) if systolic else None,
        diastolic_bp=float(diastolic) if diastolic else None,
        pulse=float(pulse) if pulse else None,
        spo2=float(spo2) if spo2 else None,
        temperature_c=float(temperature_c) if temperature_c else None,
        fasting_glucose=float(fasting_glucose) if fasting_glucose else None,
        source="nurse_bedside_monitor",
        notes=f"Bedside vitals recorded by {current_user.full_name or 'Nurse'}. {notes or ''}".strip(),
        created_at=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()

    # Clinical Threshold Alert Evaluation
    threshold_alerts = []
    if spo2 and float(spo2) < 92:
        threshold_alerts.append({
            "parameter": "SpO2",
            "value": f"{spo2}%",
            "severity": "CRITICAL",
            "alert": "Acute Hypoxemia Detected (< 92%). Initiate high-flow O2 and escalate to attending."
        })
    if systolic and (float(systolic) >= 160 or float(systolic) <= 90):
        threshold_alerts.append({
            "parameter": "Blood Pressure",
            "value": f"{systolic}/{diastolic} mmHg",
            "severity": "CRITICAL" if float(systolic) >= 180 else "URGENT",
            "alert": "Severe Hypertensive Urgency" if float(systolic) >= 160 else "Hypotension / Shock Risk"
        })
    if pulse and (float(pulse) >= 110 or float(pulse) <= 50):
        threshold_alerts.append({
            "parameter": "Heart Rate",
            "value": f"{pulse} bpm",
            "severity": "URGENT",
            "alert": "Tachycardia (> 110 bpm)" if float(pulse) >= 110 else "Bradycardia (< 50 bpm)"
        })
    if temperature_c and float(temperature_c) >= 38.5:
        threshold_alerts.append({
            "parameter": "Temperature",
            "value": f"{temperature_c} °C",
            "severity": "URGENT",
            "alert": "High Grade Pyrexia (>= 38.5 °C). Blood cultures & antipyretic review required."
        })

    log_audit_event(db, current_user, "NURSE_VITALS_RECORDED", patient_id, f"SpO2: {spo2}, BP: {systolic}/{diastolic}")

    return {
        "status": "success",
        "message": "Bedside vitals successfully recorded to patient EHR.",
        "log_id": log_entry.id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "threshold_alerts": threshold_alerts,
        "alert_triggered": len(threshold_alerts) > 0
    }


@router.get("/handovers", response_model=List[ShiftHandoverRead])
def list_shift_handovers(
    ward: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List structured SBAR shift handover notes for clinical continuity.
    """
    query = db.query(ShiftHandover)
    if ward and ward.lower() != "all":
        query = query.filter(ShiftHandover.ward.ilike(f"%{ward}%"))

    handovers = query.order_by(ShiftHandover.created_at.desc()).limit(20).all()

    output = []
    for h in handovers:
        alerts = json.loads(h.critical_alerts_json) if h.critical_alerts_json else []
        output.append(ShiftHandoverRead(
            handover_id=h.handover_id,
            ward=h.ward,
            shift_type=h.shift_type,
            outgoing_nurse_id=h.outgoing_nurse_id,
            outgoing_nurse_name=h.outgoing_nurse_name,
            incoming_nurse_id=h.incoming_nurse_id,
            incoming_nurse_name=h.incoming_nurse_name,
            handover_date=str(h.handover_date),
            situation=h.situation,
            background=h.background,
            assessment=h.assessment,
            recommendation=h.recommendation,
            critical_alerts=alerts,
            total_patients=h.total_patients,
            created_at=h.created_at.isoformat()
        ))
    return output


@router.post("/handovers", response_model=ShiftHandoverRead, status_code=status.HTTP_201_CREATED)
def submit_shift_handover(
    payload: ShiftHandoverCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit structured SBAR (Situation, Background, Assessment, Recommendation) shift handover.
    """
    handover_id = f"HND-{uuid.uuid4().hex[:10].upper()}"
    nurse_name = current_user.full_name or payload.outgoing_nurse_name

    handover = ShiftHandover(
        handover_id=handover_id,
        ward=payload.ward,
        shift_type=payload.shift_type,
        outgoing_nurse_id=current_user.username,
        outgoing_nurse_name=nurse_name,
        incoming_nurse_id=payload.incoming_nurse_id,
        incoming_nurse_name=payload.incoming_nurse_name,
        handover_date=payload.handover_date,
        situation=payload.situation,
        background=payload.background,
        assessment=payload.assessment,
        recommendation=payload.recommendation,
        critical_alerts_json=json.dumps(payload.critical_alerts),
        total_patients=payload.total_patients,
        created_at=datetime.now(timezone.utc)
    )
    db.add(handover)
    db.commit()
    db.refresh(handover)

    log_audit_event(db, current_user, "SHIFT_HANDOVER_SUBMITTED", handover_id, f"Ward: {payload.ward}, Shift: {payload.shift_type}")

    return ShiftHandoverRead(
        handover_id=handover.handover_id,
        ward=handover.ward,
        shift_type=handover.shift_type,
        outgoing_nurse_id=handover.outgoing_nurse_id,
        outgoing_nurse_name=handover.outgoing_nurse_name,
        incoming_nurse_id=handover.incoming_nurse_id,
        incoming_nurse_name=handover.incoming_nurse_name,
        handover_date=str(handover.handover_date),
        situation=handover.situation,
        background=handover.background,
        assessment=handover.assessment,
        recommendation=handover.recommendation,
        critical_alerts=payload.critical_alerts,
        total_patients=handover.total_patients,
        created_at=handover.created_at.isoformat()
    )
