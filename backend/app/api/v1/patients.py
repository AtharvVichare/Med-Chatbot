from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.app.db.session import get_db
from backend.app.db.models import (
    Patient,
    Encounter,
    Condition,
    Observation,
    Medication,
    RiskAssessment,
    Allergy,
    FamilyMember,
    FamilyCondition,
    DailyHealthLog,
    PatientDocument
)
from backend.app.db.schemas import (
    PatientRead,
    PatientSelfUpdate,
    EncounterRead,
    ConditionRead,
    ConditionCreatePatient,
    ObservationRead,
    MedicationRead,
    MedicationCreatePatient,
    RiskAssessmentRead,
    AllergyCreate,
    AllergyRead,
    FamilyMemberCreate,
    FamilyMemberRead,
    DailyHealthLogCreate,
    DailyHealthLogRead,
    PatientDocumentRead
)
from backend.app.schemas.api_schemas import (
    TimelineResponse,
    TimelineEvent,
    PaginatedResponse,
    LongitudinalGraphResponse,
    ObservationTrendPoint
)
from backend.app.core.dependencies import get_current_user, verify_patient_access
from backend.app.core.demo_users import User

router = APIRouter(prefix="/patients", tags=["Patients EHR"])

@router.get("", response_model=PaginatedResponse)
def list_patients(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    district: Optional[str] = Query(None, description="Filter by district"),
    sex: Optional[str] = Query(None, description="Filter by gender (Male/Female)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List patient records with pagination and filtering.
    - Public health analysts: Forbidden from identifiable list.
    - Patients: May only see their own record.
    - Doctors: May see only their assigned patients.
    - Administrators: Can see all patients.
    """
    if current_user.role == "public_health_analyst":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public health analysts are prohibited from accessing identifiable patient lists."
        )

    stmt = select(Patient)

    if current_user.role == "patient":
        stmt = stmt.where(Patient.patient_id == current_user.patient_id)
    elif current_user.role == "doctor":
        stmt = stmt.where(Patient.patient_id.in_(current_user.assigned_patients))

    if district:
        stmt = stmt.where(Patient.district == district)
    if sex:
        stmt = stmt.where(Patient.sex == sex)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    patients = db.scalars(
        stmt.order_by(Patient.registered_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    serialized = [PatientRead.model_validate(p) for p in patients]
    return PaginatedResponse(total=total or 0, page=page, page_size=page_size, data=serialized)


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id))
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {patient_id} not found")
    res = PatientRead.model_validate(patient)
    res.phone_number = patient.contact_no
    return res


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient_profile(
    patient_id: str,
    update_data: PatientSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id))
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {patient_id} not found")
    
    if update_data.first_name is not None:
        patient.first_name = update_data.first_name
    if update_data.last_name is not None:
        patient.last_name = update_data.last_name
    if update_data.phone_number is not None:
        patient.contact_no = update_data.phone_number
    elif update_data.contact_no is not None:
        patient.contact_no = update_data.contact_no
    if update_data.district is not None:
        patient.district = update_data.district
    if update_data.state is not None:
        patient.state = update_data.state
    if update_data.is_smoker is not None:
        patient.is_smoker = update_data.is_smoker

    db.commit()
    db.refresh(patient)
    res = PatientRead.model_validate(patient)
    res.phone_number = patient.contact_no
    return res


@router.get("/{patient_id}/timeline", response_model=TimelineResponse)
def get_patient_timeline(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    """
    Unified Longitudinal Patient Timeline:
    Aggregates encounters, diagnoses, observations, and medications
    sorted strictly in chronological order without N+1 query overhead.
    """
    patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id))
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {patient_id} not found")

    encounters = db.scalars(select(Encounter).where(Encounter.patient_id == patient_id)).all()
    conditions = db.scalars(select(Condition).where(Condition.patient_id == patient_id)).all()
    observations = db.scalars(select(Observation).where(Observation.patient_id == patient_id)).all()
    medications = db.scalars(select(Medication).where(Medication.patient_id == patient_id)).all()

    timeline_events: List[TimelineEvent] = []

    # 1. Encounters
    for enc in encounters:
        timeline_events.append(TimelineEvent(
            event_id=enc.encounter_id,
            event_type="encounter",
            patient_id=patient_id,
            encounter_id=enc.encounter_id,
            event_date=enc.encounter_date,
            clinical_details={
                "facility": enc.facility,
                "encounter_type": enc.encounter_type,
                "attending_provider": enc.attending_provider
            },
            source_table="encounters"
        ))

    # 2. Conditions
    for cond in conditions:
        timeline_events.append(TimelineEvent(
            event_id=cond.condition_id,
            event_type="condition",
            patient_id=patient_id,
            encounter_id=None,
            event_date=cond.onset_date,
            clinical_details={
                "diagnosis_code": cond.diagnosis_code,
                "diagnosis_name": cond.diagnosis_name,
                "clinical_status": cond.clinical_status
            },
            source_table="conditions"
        ))

    # 3. Observations
    for obs in observations:
        timeline_events.append(TimelineEvent(
            event_id=obs.observation_id,
            event_type="observation",
            patient_id=patient_id,
            encounter_id=obs.encounter_id,
            event_date=obs.date,
            clinical_details={
                "test_code": obs.test_code,
                "test_name": obs.test_name,
                "value_numeric": obs.value_numeric,
                "unit": obs.unit,
                "reference_range": obs.reference_range,
                "interpretation": obs.interpretation
            },
            source_table="observations"
        ))

    # 4. Medications
    for med in medications:
        timeline_events.append(TimelineEvent(
            event_id=med.medication_id,
            event_type="medication",
            patient_id=patient_id,
            encounter_id=med.encounter_id,
            event_date=med.start_date,
            clinical_details={
                "medication_code": med.medication_code,
                "medication_name": med.medication_name,
                "dosage": med.dosage,
                "end_date": str(med.end_date) if med.end_date else None,
                "status": med.status
            },
            source_table="medications"
        ))

    # Sort strictly by event_date ascending
    timeline_events.sort(key=lambda ev: ev.event_date)

    return TimelineResponse(
        patient_id=patient_id,
        total_events=len(timeline_events),
        events=timeline_events
    )


@router.get("/{patient_id}/encounters", response_model=List[EncounterRead])
def get_patient_encounters(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    encounters = db.scalars(
        select(Encounter)
        .where(Encounter.patient_id == patient_id)
        .order_by(Encounter.encounter_date.asc())
    ).all()
    return [EncounterRead.model_validate(e) for e in encounters]


@router.get("/{patient_id}/conditions", response_model=List[ConditionRead])
def get_patient_conditions(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    conditions = db.scalars(
        select(Condition)
        .where(Condition.patient_id == patient_id)
        .order_by(Condition.onset_date.asc())
    ).all()
    return [ConditionRead.model_validate(c) for c in conditions]


@router.get("/{patient_id}/observations", response_model=List[ObservationRead])
def get_patient_observations(
    patient_id: str,
    test_code: Optional[str] = Query(None, description="Filter by LOINC test code"),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    stmt = select(Observation).where(Observation.patient_id == patient_id)
    if test_code:
        stmt = stmt.where(Observation.test_code == test_code)
    observations = db.scalars(stmt.order_by(Observation.date.asc())).all()
    return [ObservationRead.model_validate(o) for o in observations]


@router.get("/{patient_id}/longitudinal-trends", response_model=LongitudinalGraphResponse)
def get_patient_longitudinal_trends(
    patient_id: str,
    metric: str = Query("blood_pressure", description="Metric to graph: 'blood_pressure', 'systolic_bp', 'diastolic_bp', 'glucose', 'hba1c', 'oxygen_saturation', 'pulse'"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD start filter"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD end filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    """
    Returns authenticated longitudinal patient health measurements aggregated across
    clinical lab observations and daily self-tracking logs.
    Strictly chronological, preserved units, zero fabricated values.
    """
    normalized_metric = metric.strip().lower()
    points: List[ObservationTrendPoint] = []
    unit = ""
    display_title = ""

    # 1. Query clinical lab observations
    obs_query = select(Observation).where(Observation.patient_id == patient_id)
    if start_date:
        obs_query = obs_query.where(Observation.date >= start_date)
    if end_date:
        obs_query = obs_query.where(Observation.date <= end_date)

    if normalized_metric in {"systolic_bp", "blood_pressure"}:
        unit = "mmHg"
        display_title = "Systolic Blood Pressure Trend"
        obs_rows = db.scalars(obs_query.where(Observation.test_code == "8480-6").order_by(Observation.date.asc())).all()
        for r in obs_rows:
            if r.value_numeric is not None:
                points.append(ObservationTrendPoint(
                    date=str(r.date),
                    value=float(r.value_numeric),
                    unit="mmHg",
                    source_type="lab_observation",
                    reference_range=r.reference_range,
                    interpretation=r.interpretation,
                    test_name="Systolic Blood Pressure"
                ))
    elif normalized_metric == "diastolic_bp":
        unit = "mmHg"
        display_title = "Diastolic Blood Pressure Trend"
        obs_rows = db.scalars(obs_query.where(Observation.test_code == "8462-4").order_by(Observation.date.asc())).all()
        for r in obs_rows:
            if r.value_numeric is not None:
                points.append(ObservationTrendPoint(
                    date=str(r.date),
                    value=float(r.value_numeric),
                    unit="mmHg",
                    source_type="lab_observation",
                    reference_range=r.reference_range,
                    interpretation=r.interpretation,
                    test_name="Diastolic Blood Pressure"
                ))
    elif normalized_metric in {"glucose", "blood_glucose", "fasting_glucose"}:
        unit = "mg/dL"
        display_title = "Fasting Blood Glucose Trend"
        obs_rows = db.scalars(obs_query.where(Observation.test_code == "1558-6").order_by(Observation.date.asc())).all()
        for r in obs_rows:
            if r.value_numeric is not None:
                points.append(ObservationTrendPoint(
                    date=str(r.date),
                    value=float(r.value_numeric),
                    unit="mg/dL",
                    source_type="lab_observation",
                    reference_range=r.reference_range,
                    interpretation=r.interpretation,
                    test_name="Fasting Glucose"
                ))
    elif normalized_metric == "hba1c":
        unit = "%"
        display_title = "HbA1c (Glycated Hemoglobin) Trend"
        obs_rows = db.scalars(obs_query.where(Observation.test_code == "4548-4").order_by(Observation.date.asc())).all()
        for r in obs_rows:
            if r.value_numeric is not None:
                points.append(ObservationTrendPoint(
                    date=str(r.date),
                    value=float(r.value_numeric),
                    unit="%",
                    source_type="lab_observation",
                    reference_range=r.reference_range,
                    interpretation=r.interpretation,
                    test_name="Hemoglobin A1c"
                ))
    elif normalized_metric in {"oxygen_saturation", "spo2"}:
        unit = "%"
        display_title = "Oxygen Saturation (SpO2) Trend"
        obs_rows = db.scalars(obs_query.where(Observation.test_code == "59408-5").order_by(Observation.date.asc())).all()
        for r in obs_rows:
            if r.value_numeric is not None:
                points.append(ObservationTrendPoint(
                    date=str(r.date),
                    value=float(r.value_numeric),
                    unit="%",
                    source_type="lab_observation",
                    reference_range=r.reference_range,
                    interpretation=r.interpretation,
                    test_name="Pulse Oximetry SpO2"
                ))

    # 2. Query patient self-reported DailyHealthLog
    daily_query = select(DailyHealthLog).where(DailyHealthLog.patient_id == patient_id)
    if start_date:
        daily_query = daily_query.where(DailyHealthLog.log_date >= start_date)
    if end_date:
        daily_query = daily_query.where(DailyHealthLog.log_date <= end_date)
    daily_rows = db.scalars(daily_query.order_by(DailyHealthLog.log_date.asc())).all()

    for d in daily_rows:
        d_str = str(d.log_date)
        if normalized_metric in {"systolic_bp", "blood_pressure"} and d.systolic_bp is not None:
            points.append(ObservationTrendPoint(
                date=d_str,
                value=float(d.systolic_bp),
                unit="mmHg",
                source_type="home_daily_log",
                reference_range="90-120 mmHg",
                interpretation=None,
                test_name="Home Systolic BP"
            ))
        elif normalized_metric == "diastolic_bp" and d.diastolic_bp is not None:
            points.append(ObservationTrendPoint(
                date=d_str,
                value=float(d.diastolic_bp),
                unit="mmHg",
                source_type="home_daily_log",
                reference_range="60-80 mmHg",
                interpretation=None,
                test_name="Home Diastolic BP"
            ))
        elif normalized_metric in {"glucose", "blood_glucose", "fasting_glucose"} and d.fasting_glucose is not None:
            points.append(ObservationTrendPoint(
                date=d_str,
                value=float(d.fasting_glucose),
                unit="mg/dL",
                source_type="home_daily_log",
                reference_range="70-99 mg/dL",
                interpretation=None,
                test_name="Home Fasting Glucose"
            ))
        elif normalized_metric == "pulse" and d.pulse is not None:
            unit = "bpm"
            display_title = "Resting Pulse Trend"
            points.append(ObservationTrendPoint(
                date=d_str,
                value=float(d.pulse),
                unit="bpm",
                source_type="home_daily_log",
                reference_range="60-100 bpm",
                interpretation=None,
                test_name="Home Pulse"
            ))

    # Sort strictly chronologically by date
    points.sort(key=lambda p: p.date)

    latest_val = points[-1].value if points else None
    prev_val = points[-2].value if len(points) >= 2 else None
    change_val = round(latest_val - prev_val, 2) if (latest_val is not None and prev_val is not None) else None
    
    change_dir = "stable"
    if change_val is not None:
        if change_val > 0.05:
            change_dir = "increased"
        elif change_val < -0.05:
            change_dir = "decreased"

    latest_dt = points[-1].date if points else None

    return LongitudinalGraphResponse(
        patient_id=patient_id,
        test_category=normalized_metric,
        metric_name=display_title or metric.replace("_", " ").title(),
        unit=unit,
        points_count=len(points),
        data=points,
        latest_value=latest_val,
        previous_value=prev_val,
        change_value=change_val,
        change_direction=change_dir if points else None,
        latest_date=latest_dt,
        disclaimer="Longitudinal measurements reflect historical clinical observations and daily home tracking logs. Individual readings do not constitute a standalone diagnosis."
    )


@router.get("/{patient_id}/medications", response_model=List[MedicationRead])
def get_patient_medications(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    medications = db.scalars(
        select(Medication)
        .where(Medication.patient_id == patient_id)
        .order_by(Medication.start_date.asc())
    ).all()
    return [MedicationRead.model_validate(m) for m in medications]


@router.get("/{patient_id}/risk-assessments", response_model=List[RiskAssessmentRead])
def get_patient_risk_assessments(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    risks = db.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.patient_id == patient_id)
        .order_by(RiskAssessment.assessment_date.desc())
    ).all()
    return [RiskAssessmentRead.model_validate(r) for r in risks]


# ==========================================
# Patient-Controlled Longitudinal EHR Updates
# ==========================================

import uuid

@router.post("/{patient_id}/conditions", response_model=ConditionRead, status_code=status.HTTP_201_CREATED)
def add_patient_condition(
    patient_id: str,
    cond: ConditionCreatePatient,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    diag_code = cond.condition_code or cond.diagnosis_code or "PATIENT-REPORTED"
    diag_name = cond.condition_name or cond.diagnosis_name or "Unspecified condition"
    new_cond = Condition(
        condition_id=f"COND-{uuid.uuid4().hex[:8].upper()}",
        patient_id=patient_id,
        diagnosis_code=diag_code,
        diagnosis_name=diag_name,
        onset_date=cond.onset_date,
        clinical_status=cond.clinical_status,
        is_synthetic=False
    )
    db.add(new_cond)
    db.commit()
    db.refresh(new_cond)
    return ConditionRead.model_validate(new_cond)


@router.post("/{patient_id}/medications", response_model=MedicationRead, status_code=status.HTTP_201_CREATED)
def add_patient_medication(
    patient_id: str,
    med: MedicationCreatePatient,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    latest_enc = db.scalar(
        select(Encounter)
        .where(Encounter.patient_id == patient_id)
        .order_by(Encounter.encounter_date.desc())
    )
    enc_id = latest_enc.encounter_id if latest_enc else None
    if not enc_id:
        enc_id = f"ENC-{uuid.uuid4().hex[:8].upper()}"
        dummy_enc = Encounter(
            encounter_id=enc_id,
            patient_id=patient_id,
            encounter_date=date.today(),
            facility="Patient Portal Self-Report",
            district="Self",
            encounter_type="PATIENT_REPORTED",
            is_synthetic=False
        )
        db.add(dummy_enc)
        db.flush()

    new_med = Medication(
        medication_id=f"MED-{uuid.uuid4().hex[:8].upper()}",
        encounter_id=enc_id,
        patient_id=patient_id,
        medication_code="MED-SELF",
        medication_name=med.medication_name,
        dosage=f"{med.dosage} ({med.frequency})" if med.frequency else med.dosage,
        start_date=med.start_date,
        status=med.status,
        is_synthetic=False
    )
    db.add(new_med)
    db.commit()
    db.refresh(new_med)
    return MedicationRead.model_validate(new_med)


@router.patch("/{patient_id}/medications/{medication_id}/discontinue", response_model=MedicationRead)
def discontinue_patient_medication(
    patient_id: str,
    medication_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    med = db.scalar(select(Medication).where((Medication.medication_id == medication_id) & (Medication.patient_id == patient_id)))
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication record not found")
    med.status = "discontinued"
    med.end_date = date.today()
    db.commit()
    db.refresh(med)
    return MedicationRead.model_validate(med)


@router.get("/{patient_id}/allergies", response_model=List[AllergyRead])
def get_patient_allergies(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    allergies = db.scalars(
        select(Allergy)
        .where(Allergy.patient_id == patient_id)
        .order_by(Allergy.recorded_date.desc())
    ).all()
    return [AllergyRead.model_validate(a) for a in allergies]


@router.post("/{patient_id}/allergies", response_model=AllergyRead, status_code=status.HTTP_201_CREATED)
def add_patient_allergy(
    patient_id: str,
    req: AllergyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    allergy = Allergy(
        allergy_id=f"ALL-{uuid.uuid4().hex[:8].upper()}",
        patient_id=patient_id,
        substance=req.substance,
        reaction=req.reaction,
        severity=req.severity,
        category=req.category,
        verification_status=req.verification_status,
        recorded_date=req.recorded_date,
        notes=req.notes
    )
    db.add(allergy)
    db.commit()
    db.refresh(allergy)
    return AllergyRead.model_validate(allergy)


@router.delete("/{patient_id}/allergies/{allergy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_allergy(
    patient_id: str,
    allergy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    allergy = db.scalar(select(Allergy).where((Allergy.allergy_id == allergy_id) & (Allergy.patient_id == patient_id)))
    if allergy:
        db.delete(allergy)
        db.commit()
    return None


# ==========================================
# Family Health History Endpoints
# ==========================================

@router.get("/{patient_id}/family-history", response_model=List[FamilyMemberRead])
def get_family_history(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    members = db.scalars(
        select(FamilyMember)
        .where(FamilyMember.patient_id == patient_id)
        .order_by(FamilyMember.created_at.asc())
    ).all()
    return [FamilyMemberRead.model_validate(m) for m in members]


@router.post("/{patient_id}/family-history", response_model=FamilyMemberRead, status_code=status.HTTP_201_CREATED)
def add_family_member(
    patient_id: str,
    req: FamilyMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    member_id = f"FAM-{uuid.uuid4().hex[:8].upper()}"
    member = FamilyMember(
        id=member_id,
        patient_id=patient_id,
        relative_name=req.relative_name,
        relation_type=req.relation_type,
        lineage=req.lineage,
        is_deceased=req.is_deceased,
        notes=req.notes
    )
    db.add(member)
    db.flush()

    if req.conditions:
        for c in req.conditions:
            cond_rec = FamilyCondition(
                id=f"FC-{uuid.uuid4().hex[:8].upper()}",
                family_member_id=member_id,
                condition_name=c.condition_name,
                approximate_age_at_onset=c.approximate_age_at_onset,
                notes=c.notes
            )
            db.add(cond_rec)

    db.commit()
    db.refresh(member)
    return FamilyMemberRead.model_validate(member)


@router.delete("/{patient_id}/family-history/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_family_member(
    patient_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    member = db.scalar(select(FamilyMember).where((FamilyMember.id == member_id) & (FamilyMember.patient_id == patient_id)))
    if member:
        db.delete(member)
        db.commit()
    return None


# ==========================================
# Daily Health Tracking Endpoints
# ==========================================

@router.get("/{patient_id}/daily-tracking", response_model=List[DailyHealthLogRead])
def get_daily_logs(
    patient_id: str,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    logs = db.scalars(
        select(DailyHealthLog)
        .where(DailyHealthLog.patient_id == patient_id)
        .order_by(DailyHealthLog.log_date.desc())
        .limit(limit)
    ).all()
    return [DailyHealthLogRead.model_validate(l) for l in logs]


@router.post("/{patient_id}/daily-tracking", response_model=DailyHealthLogRead, status_code=status.HTTP_201_CREATED)
def record_daily_health_log(
    patient_id: str,
    req: DailyHealthLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
    new_log = DailyHealthLog(
        id=log_id,
        patient_id=patient_id,
        log_date=req.log_date,
        systolic_bp=req.systolic_bp,
        diastolic_bp=req.diastolic_bp,
        pulse=req.pulse,
        fasting_glucose=req.fasting_glucose,
        post_meal_glucose=req.post_meal_glucose,
        weight_kg=req.weight_kg,
        temperature_c=req.temperature_c,
        spo2=req.spo2,
        sleep_hours=req.sleep_hours,
        mood=req.mood,
        steps_count=req.steps_count,
        source=req.source,
        notes=req.notes
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return DailyHealthLogRead.model_validate(new_log)


# ==========================================
# Patient Documents Metadata Endpoints
# ==========================================

@router.get("/{patient_id}/documents", response_model=List[PatientDocumentRead])
def get_patient_documents(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_patient_access)
):
    docs = db.scalars(
        select(PatientDocument)
        .where(PatientDocument.patient_id == patient_id)
        .order_by(PatientDocument.created_at.desc())
    ).all()
    return [PatientDocumentRead.model_validate(d) for d in docs]


