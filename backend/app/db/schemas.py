from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

class PatientBase(BaseModel):
    patient_id: str
    abha_number: str
    first_name: str
    last_name: str
    birth_date: date
    age: int
    sex: str
    state: str
    district: str
    contact_no: Optional[str] = None
    phone_number: Optional[str] = None
    registered_date: date
    is_smoker: bool = False
    is_synthetic: bool = True
    data_source: str = "SYNTHETIC_SIMULATION"
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None

    @model_validator(mode="after")
    def sync_patient_aliases(self):
        if not self.gender and self.sex:
            self.gender = self.sex
        if not self.sex and self.gender:
            self.sex = self.gender
        if not self.date_of_birth and self.birth_date:
            self.date_of_birth = self.birth_date
        if not self.birth_date and self.date_of_birth:
            self.birth_date = self.date_of_birth
        if not self.phone_number and self.contact_no:
            self.phone_number = self.contact_no
        if not self.contact_no and self.phone_number:
            self.contact_no = self.phone_number
        return self

class PatientCreate(PatientBase):
    pass

class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime


class EncounterBase(BaseModel):
    encounter_id: str
    patient_id: str
    encounter_date: date
    facility: str
    district: str
    encounter_type: str
    attending_provider: Optional[str] = None
    is_synthetic: bool = True

class EncounterCreate(EncounterBase):
    pass

class EncounterRead(EncounterBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime


class ConditionBase(BaseModel):
    condition_id: str
    patient_id: str
    diagnosis_code: str
    diagnosis_name: str
    onset_date: date
    clinical_status: str = "active"
    is_synthetic: bool = True

class ConditionCreate(ConditionBase):
    pass

class ConditionRead(ConditionBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime


class ObservationBase(BaseModel):
    observation_id: str
    encounter_id: str
    patient_id: str
    test_code: str
    test_name: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    interpretation: Optional[str] = None
    date: date
    is_synthetic: bool = True

class ObservationCreate(ObservationBase):
    pass

class ObservationRead(ObservationBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime


class MedicationBase(BaseModel):
    medication_id: str
    encounter_id: str
    patient_id: str
    indication_condition_code: Optional[str] = None
    medication_code: str
    medication_name: str
    dosage: str
    start_date: date
    end_date: Optional[date] = None
    status: str = "active"
    is_synthetic: bool = True

class MedicationCreate(MedicationBase):
    pass

class MedicationRead(MedicationBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime


class RiskAssessmentBase(BaseModel):
    assessment_id: str
    patient_id: str
    model_version: str
    model_type: str = "SIMULATED_HEURISTIC"
    risk_type: str
    score: float
    risk_category: str
    assessment_date: date
    model_documentation: Optional[str] = None
    is_synthetic: bool = True

class RiskAssessmentCreate(RiskAssessmentBase):
    pass

class RiskAssessmentRead(RiskAssessmentBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime


class AuditLogBase(BaseModel):
    log_id: str
    user_id: str
    action: str
    record_id: str
    record_type: str
    facility: Optional[str] = None
    timestamp: datetime
    is_synthetic: bool = True

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogRead(AuditLogBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime


# ==========================================
# Schema Models for Comprehensive Platform
# ==========================================

class AllergyBase(BaseModel):
    substance: str
    reaction: str
    severity: str = "moderate"
    category: str = "drug"
    verification_status: str = "patient_reported"
    recorded_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None

class AllergyCreate(AllergyBase):
    pass

class AllergyRead(AllergyBase):
    model_config = ConfigDict(from_attributes=True)
    allergy_id: str
    patient_id: str
    created_at: datetime


class FamilyConditionBase(BaseModel):
    condition_name: str
    approximate_age_at_onset: Optional[int] = None
    notes: Optional[str] = None

class FamilyConditionCreate(FamilyConditionBase):
    pass

class FamilyConditionRead(FamilyConditionBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    family_member_id: str
    created_at: datetime


class FamilyMemberBase(BaseModel):
    relative_name: Optional[str] = None
    relation_type: str
    lineage: Optional[str] = None
    is_deceased: bool = False
    notes: Optional[str] = None

class FamilyMemberCreate(FamilyMemberBase):
    conditions: Optional[List[FamilyConditionCreate]] = []

class FamilyMemberRead(FamilyMemberBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    patient_id: str
    created_at: datetime
    conditions: List[FamilyConditionRead] = []


class DailyHealthLogBase(BaseModel):
    log_date: date = Field(default_factory=date.today)
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    pulse: Optional[float] = None
    fasting_glucose: Optional[float] = None
    post_meal_glucose: Optional[float] = None
    weight_kg: Optional[float] = None
    temperature_c: Optional[float] = None
    spo2: Optional[float] = None
    sleep_hours: Optional[float] = None
    mood: Optional[str] = None
    steps_count: Optional[int] = None
    source: str = "patient_manual"
    notes: Optional[str] = None

class DailyHealthLogCreate(DailyHealthLogBase):
    pass

class DailyHealthLogRead(DailyHealthLogBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    patient_id: str
    created_at: datetime


class PatientDocumentBase(BaseModel):
    file_name: str
    file_type: str
    document_type: str = "laboratory_report"
    report_date: Optional[date] = None

class PatientDocumentRead(PatientDocumentBase):
    model_config = ConfigDict(from_attributes=True)
    document_id: str
    patient_id: str
    file_size_bytes: int
    extracted_text: Optional[str] = None
    extracted_metadata: Optional[str] = None
    confirmation_status: str
    created_at: datetime


class ChatMessageBase(BaseModel):
    sender: str
    content: str
    proposed_ehr_actions: Optional[str] = None
    is_confirmed_to_ehr: bool = False

class ChatMessageCreate(BaseModel):
    content: str
    attachments: Optional[List[str]] = None

class ChatMessageRead(ChatMessageBase):
    model_config = ConfigDict(from_attributes=True)
    message_id: str
    conversation_id: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class ChatConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    conversation_id: str
    patient_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageRead]] = []

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    @field_serializer("updated_at")
    def serialize_updated_at(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class PatientSelfUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    contact_no: Optional[str] = None
    phone_number: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    is_smoker: Optional[bool] = None
    sex: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    date_of_birth: Optional[date] = None

class ConditionCreatePatient(BaseModel):
    diagnosis_name: Optional[str] = None
    condition_name: Optional[str] = None
    diagnosis_code: Optional[str] = "PATIENT-REPORTED"
    condition_code: Optional[str] = None
    onset_date: date = Field(default_factory=date.today)
    clinical_status: str = "active"
    category: Optional[str] = None

class MedicationCreatePatient(BaseModel):
    medication_name: str
    dosage: str
    frequency: str
    route: str = "oral"
    start_date: date = Field(default_factory=date.today)
    status: str = "active"
    notes: Optional[str] = None


# ============================================================================
# EXTENDED HMS SCHEMAS: FAMILY LINKS, CLINICAL WORKSPACE & NURSING WORKSPACE
# ============================================================================

class FamilyLinkRequestCreate(BaseModel):
    target_patient_id: str
    relationship_type: str  # spouse, parent, child, sibling, guardian, other
    permissions: List[str] = [
        "view_basic_health",
        "view_medical_history",
        "view_reports",
        "manage_appointments",
        "receive_reminders",
        "assist_admissions",
        "access_documents"
    ]
    notes: Optional[str] = None

class FamilyLinkRespondRequest(BaseModel):
    action: str  # approve, reject
    permissions: Optional[List[str]] = None
    notes: Optional[str] = None

class FamilyLinkPermissionsUpdate(BaseModel):
    permissions: List[str]

class FamilyLinkRead(BaseModel):
    link_id: str
    requester_patient_id: str
    target_patient_id: str
    requester_name: Optional[str] = None
    target_name: Optional[str] = None
    relationship_type: str
    status: str
    permissions: List[str] = []
    requested_at: str
    responded_at: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ClinicalNoteCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    note_type: str = "progress_note"  # consultation, progress_note, soap_note, discharge_summary, treatment_plan, referral
    title: str
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    content: str

class ClinicalNoteRead(BaseModel):
    note_id: str
    patient_id: str
    patient_name: Optional[str] = None
    encounter_id: Optional[str] = None
    doctor_id: str
    doctor_name: str
    note_type: str
    title: str
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    content: str
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

class ClinicalOrderCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    order_type: str  # lab, imaging, procedure, nursing_intervention
    order_name: str
    clinical_indication: Optional[str] = None
    priority: str = "routine"  # routine, urgent, stat

class ClinicalOrderRead(BaseModel):
    order_id: str
    patient_id: str
    patient_name: Optional[str] = None
    encounter_id: Optional[str] = None
    doctor_id: str
    doctor_name: str
    order_type: str
    order_name: str
    clinical_indication: Optional[str] = None
    priority: str
    status: str
    result_summary: Optional[str] = None
    ordered_at: str
    completed_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class NursingTaskCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    ward: str
    bed_number: Optional[str] = None
    task_type: str  # medication, vitals, lab_collection, wound_care, procedure_prep, doctor_order, admission_discharge
    title: str
    description: Optional[str] = None
    priority: str = "routine"  # routine, urgent, stat
    scheduled_time: datetime
    assigned_nurse_id: Optional[str] = None
    assigned_nurse_name: Optional[str] = None

class NursingTaskUpdate(BaseModel):
    status: Optional[str] = None  # in_progress, completed, overdue, cancelled
    completion_notes: Optional[str] = None
    assigned_nurse_id: Optional[str] = None
    assigned_nurse_name: Optional[str] = None

class NursingTaskRead(BaseModel):
    task_id: str
    patient_id: str
    patient_name: Optional[str] = None
    encounter_id: Optional[str] = None
    ward: str
    bed_number: Optional[str] = None
    task_type: str
    title: str
    description: Optional[str] = None
    priority: str
    scheduled_time: str
    status: str
    assigned_nurse_id: Optional[str] = None
    assigned_nurse_name: Optional[str] = None
    completed_at: Optional[str] = None
    completed_by: Optional[str] = None
    completion_notes: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class MedicationAdministrationCreate(BaseModel):
    patient_id: str
    medication_id: Optional[str] = None
    medication_name: str
    dosage: str
    route: str = "oral"
    scheduled_time: datetime
    notes: Optional[str] = None

class MedicationAdministrationRecordAction(BaseModel):
    status: str  # administered, delayed, refused, missed
    reason: Optional[str] = None
    notes: Optional[str] = None

class MedicationAdministrationRead(BaseModel):
    mar_id: str
    patient_id: str
    patient_name: Optional[str] = None
    medication_id: Optional[str] = None
    medication_name: str
    dosage: str
    route: str
    scheduled_time: str
    administered_time: Optional[str] = None
    administered_by: Optional[str] = None
    status: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class ShiftHandoverCreate(BaseModel):
    ward: str
    shift_type: str  # morning, evening, night
    outgoing_nurse_name: str
    incoming_nurse_id: Optional[str] = None
    incoming_nurse_name: Optional[str] = None
    handover_date: date = Field(default_factory=date.today)
    situation: str
    background: str
    assessment: str
    recommendation: str
    critical_alerts: List[str] = []
    total_patients: int = 0

class ShiftHandoverRead(BaseModel):
    handover_id: str
    ward: str
    shift_type: str
    outgoing_nurse_id: str
    outgoing_nurse_name: str
    incoming_nurse_id: Optional[str] = None
    incoming_nurse_name: Optional[str] = None
    handover_date: str
    situation: str
    background: str
    assessment: str
    recommendation: str
    critical_alerts: List[str] = []
    total_patients: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)


