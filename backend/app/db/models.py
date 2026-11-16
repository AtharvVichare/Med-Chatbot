import sys
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String(64), primary_key=True)
    abha_number = Column(String(64), nullable=False, unique=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String(16), nullable=False)
    state = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False, index=True)
    contact_no = Column(String(32), nullable=True)
    registered_date = Column(Date, nullable=False, index=True)
    is_smoker = Column(Boolean, default=False)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    data_source = Column(String(64), nullable=False, default="SYNTHETIC_SIMULATION")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    conditions = relationship("Condition", back_populates="patient", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="patient", cascade="all, delete-orphan")
    allergies = relationship("Allergy", back_populates="patient", cascade="all, delete-orphan")
    family_members = relationship("FamilyMember", back_populates="patient", cascade="all, delete-orphan")
    daily_logs = relationship("DailyHealthLog", back_populates="patient", cascade="all, delete-orphan")
    documents = relationship("PatientDocument", back_populates="patient", cascade="all, delete-orphan")
    conversations = relationship("ChatConversation", back_populates="patient", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_patients_district_state", "district", "state"),
    )


class BedRegistry(Base):
    __tablename__ = "bed_registry"

    bed_id = Column(String(64), primary_key=True)
    bed_number = Column(String(32), unique=True, nullable=False, index=True)
    ward = Column(String(64), nullable=False, index=True)
    bed_type = Column(String(64), nullable=False)
    is_occupied = Column(Boolean, default=False, nullable=False)
    current_patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_encounter_id = Column(String(64), nullable=True)
    daily_charge = Column(Float, nullable=False, default=1500.0)
    status = Column(String(32), nullable=False, default="available")  # available, occupied, maintenance, cleaning, reserved
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("Patient", foreign_keys=[current_patient_id])


class Encounter(Base):
    __tablename__ = "encounters"

    encounter_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_date = Column(Date, nullable=False, index=True)
    facility = Column(String(200), nullable=False)
    district = Column(String(100), nullable=False)
    encounter_type = Column(String(64), nullable=False)
    attending_provider = Column(String(150), nullable=True)
    assigned_bed = Column(String(64), ForeignKey("bed_registry.bed_id", ondelete="SET NULL"), nullable=True, index=True)
    encounter_status = Column(String(32), nullable=True, default=None)  # scheduled, in_progress, admitted, discharged, cancelled
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="encounters")
    bed = relationship("BedRegistry", foreign_keys=[assigned_bed])
    observations = relationship("Observation", back_populates="encounter", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="encounter", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_encounters_patient_date", "patient_id", "encounter_date"),
    )


class Condition(Base):
    __tablename__ = "conditions"

    condition_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    diagnosis_code = Column(String(32), nullable=False, index=True)
    diagnosis_name = Column(String(255), nullable=False)
    onset_date = Column(Date, nullable=False, index=True)
    clinical_status = Column(String(32), nullable=False, default="active")
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="conditions")

    __table_args__ = (
        Index("ix_conditions_patient_code", "patient_id", "diagnosis_code"),
    )


class Observation(Base):
    __tablename__ = "observations"

    observation_id = Column(String(64), primary_key=True)
    encounter_id = Column(String(64), ForeignKey("encounters.encounter_id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    test_code = Column(String(32), nullable=False, index=True)
    test_name = Column(String(255), nullable=False)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(String(255), nullable=True)
    unit = Column(String(32), nullable=True)
    reference_range = Column(String(64), nullable=True)
    interpretation = Column(String(32), nullable=True)
    date = Column(Date, nullable=False, index=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="observations")
    encounter = relationship("Encounter", back_populates="observations")

    __table_args__ = (
        Index("ix_observations_patient_test_date", "patient_id", "test_code", "date"),
    )


class Medication(Base):
    __tablename__ = "medications"

    medication_id = Column(String(64), primary_key=True)
    encounter_id = Column(String(64), ForeignKey("encounters.encounter_id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    indication_condition_code = Column(String(32), nullable=True, index=True)
    medication_code = Column(String(32), nullable=False)
    medication_name = Column(String(255), nullable=False)
    dosage = Column(String(128), nullable=False)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="active")
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="medications")
    encounter = relationship("Encounter", back_populates="medications")

    __table_args__ = (
        Index("ix_medications_patient_start", "patient_id", "start_date"),
    )


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    assessment_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    model_version = Column(String(64), nullable=False)
    model_type = Column(String(64), nullable=False, default="SIMULATED_HEURISTIC")
    risk_type = Column(String(128), nullable=False)
    score = Column(Float, nullable=False)
    risk_category = Column(String(64), nullable=False)
    assessment_date = Column(Date, nullable=False, index=True)
    model_documentation = Column(Text, nullable=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="risk_assessments")

    __table_args__ = (
        Index("ix_risk_patient_assessment_date", "patient_id", "assessment_date"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    record_id = Column(String(64), nullable=False)
    record_type = Column(String(64), nullable=False)
    facility = Column(String(200), nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_audit_user_action_timestamp", "user_id", "action", "timestamp"),
    )


# ==========================================
# Comprehensive Platform Extensions
# ==========================================

class UserAccount(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(32), nullable=False, default="patient")
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="SET NULL"), nullable=True, index=True)
    phone_number = Column(String(32), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(16), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Allergy(Base):
    __tablename__ = "allergies"

    allergy_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    substance = Column(String(150), nullable=False)
    reaction = Column(String(255), nullable=False)
    severity = Column(String(32), nullable=False, default="moderate")  # mild, moderate, severe, life-threatening
    category = Column(String(32), nullable=False, default="drug")     # drug, food, environmental, other
    verification_status = Column(String(32), nullable=False, default="patient_reported")  # patient_reported, clinician_confirmed
    recorded_date = Column(Date, nullable=False, default=date.today)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="allergies")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    relative_name = Column(String(150), nullable=True)
    relation_type = Column(String(64), nullable=False)  # father, mother, brother, sister, grandfather_maternal, etc.
    lineage = Column(String(32), nullable=True)        # maternal, paternal
    is_deceased = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="family_members")
    conditions = relationship("FamilyCondition", back_populates="family_member", cascade="all, delete-orphan")


class FamilyCondition(Base):
    __tablename__ = "family_conditions"

    id = Column(String(64), primary_key=True)
    family_member_id = Column(String(64), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True)
    condition_name = Column(String(150), nullable=False)  # Type 2 Diabetes, Hypertension, Coronary Artery Disease, etc.
    approximate_age_at_onset = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    family_member = relationship("FamilyMember", back_populates="conditions")


class DailyHealthLog(Base):
    __tablename__ = "daily_health_logs"

    id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    systolic_bp = Column(Float, nullable=True)
    diastolic_bp = Column(Float, nullable=True)
    pulse = Column(Float, nullable=True)
    fasting_glucose = Column(Float, nullable=True)
    post_meal_glucose = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    spo2 = Column(Float, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    mood = Column(String(32), nullable=True)       # excellent, good, neutral, fatigued, unwell
    steps_count = Column(Integer, nullable=True)
    source = Column(String(64), default="patient_manual", nullable=False)  # patient_manual, simulated_wearable, apple_health
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="daily_logs")

    __table_args__ = (
        Index("ix_daily_patient_date", "patient_id", "log_date"),
    )


class PatientDocument(Base):
    __tablename__ = "patient_documents"

    document_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False)      # pdf, png, jpg, jpeg
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    document_type = Column(String(64), nullable=False, default="laboratory_report")  # laboratory_report, prescription, discharge_summary, imaging_report
    report_date = Column(Date, nullable=True)
    extracted_text = Column(Text, nullable=True)
    extracted_metadata = Column(Text, nullable=True)    # JSON string containing proposed test results, reference ranges
    confirmation_status = Column(String(32), nullable=False, default="pending_review")  # pending_review, confirmed, rejected
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="documents")


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    conversation_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False, default="New Consultation")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(String(64), primary_key=True)
    conversation_id = Column(String(64), ForeignKey("chat_conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(16), nullable=False)         # user, assistant
    content = Column(Text, nullable=False)
    proposed_ehr_actions = Column(Text, nullable=True)  # JSON string of structured proposals awaiting confirmation
    is_confirmed_to_ehr = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("ChatConversation", back_populates="messages")


# ==========================================
# Hospital Management & AI-Native Architecture Models
# ==========================================

class ProcurementInventory(Base):
    __tablename__ = "procurement_inventory"

    item_id = Column(String(64), primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)  # medicine, consumable, equipment, surgical
    current_stock = Column(Integer, nullable=False, default=0)
    unit = Column(String(32), nullable=False, default="units")  # vials, boxes, strips, units, bottles
    reorder_threshold = Column(Integer, nullable=False, default=20)
    reorder_quantity = Column(Integer, nullable=False, default=100)
    unit_price = Column(Float, nullable=False, default=0.0)
    supplier_name = Column(String(150), nullable=False)
    supplier_contact = Column(String(100), nullable=True)
    expiry_date = Column(Date, nullable=True, index=True)
    batch_number = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="in_stock")  # in_stock, low_stock, critical, expired
    last_restocked_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    purchase_orders = relationship("ProcurementPurchaseOrder", back_populates="item", cascade="all, delete-orphan")


class ProcurementPurchaseOrder(Base):
    __tablename__ = "procurement_purchase_orders"

    po_id = Column(String(64), primary_key=True)
    item_id = Column(String(64), ForeignKey("procurement_inventory.item_id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    estimated_cost = Column(Float, nullable=False)
    supplier_name = Column(String(150), nullable=False)
    generated_by = Column(String(64), default="procurement_agent", nullable=False)
    status = Column(String(32), default="draft_pending_authorization", nullable=False, index=True)  # draft_pending_authorization, approved, ordered, received, rejected
    approval_notes = Column(Text, nullable=True)
    approved_by = Column(String(64), nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    item = relationship("ProcurementInventory", back_populates="purchase_orders")


class PendingEHRUpdate(Base):
    __tablename__ = "pending_ehr_updates"

    update_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_id = Column(String(64), nullable=True)
    update_type = Column(String(64), nullable=False)  # condition, medication, observation, allergy, clinical_note
    source = Column(String(64), nullable=False, default="patient_chat")  # patient_chat, voice_input, uploaded_document, doctor_portal
    source_reference_id = Column(String(64), nullable=True)
    proposed_data = Column(Text, nullable=False)  # JSON representation of clinical fields
    status = Column(String(32), nullable=False, default="pending_verification", index=True)  # pending_verification, approved, rejected, edited_and_approved
    assigned_doctor_id = Column(String(64), nullable=True, index=True)
    reviewed_by = Column(String(64), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    patient = relationship("Patient")


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    doctor_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    department = Column(String(100), nullable=False, index=True)
    specialty = Column(String(100), nullable=False, index=True)
    qualification = Column(String(150), nullable=False)
    experience_years = Column(Integer, nullable=False, default=5)
    consultation_fee = Column(Float, nullable=False, default=800.0)
    hospital_name = Column(String(150), nullable=True, default="Seth GS Medical College & KEM Hospital")
    is_available = Column(Boolean, default=True, nullable=False)
    schedule_json = Column(Text, nullable=True)  # JSON formatted available consultation slots
    profile_image_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    appointments = relationship("AppointmentBooking", back_populates="doctor")


class AppointmentBooking(Base):
    __tablename__ = "appointment_bookings"

    booking_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(String(64), ForeignKey("doctor_profiles.doctor_id", ondelete="CASCADE"), nullable=False, index=True)
    department = Column(String(100), nullable=False)
    hospital_name = Column(String(150), nullable=True, default="Seth GS Medical College & KEM Hospital")
    booking_date = Column(Date, nullable=False, index=True)
    time_slot = Column(String(32), nullable=False)
    status = Column(String(32), default="confirmed", nullable=False, index=True)  # confirmed, completed, cancelled, no_show
    chief_complaint = Column(Text, nullable=True)
    booked_via = Column(String(64), default="intake_agent", nullable=False)  # intake_agent, portal, scheduling_agent
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient")
    doctor = relationship("DoctorProfile", back_populates="appointments")

    __table_args__ = (
        UniqueConstraint("doctor_id", "booking_date", "time_slot", name="uq_doctor_date_slot"),
    )


class AdmissionRequest(Base):
    __tablename__ = "admission_requests"

    request_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(String(64), nullable=True)
    department = Column(String(100), nullable=False)
    recommended_ward = Column(String(64), nullable=False)
    assigned_bed_id = Column(String(64), ForeignKey("bed_registry.bed_id", ondelete="SET NULL"), nullable=True)
    priority = Column(String(32), default="routine", nullable=False)  # routine, urgent, emergency
    status = Column(String(32), default="pending", nullable=False, index=True)  # pending, assigned, admitted, discharged, cancelled
    admission_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    discharged_at = Column(DateTime, nullable=True)

    patient = relationship("Patient")
    bed = relationship("BedRegistry")


class BillingInvoice(Base):
    __tablename__ = "billing_invoices"

    invoice_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_id = Column(String(64), nullable=True, index=True)
    admission_id = Column(String(64), nullable=True)
    invoice_date = Column(Date, nullable=False, default=date.today)
    total_amount = Column(Float, nullable=False, default=0.0)
    insurance_covered = Column(Float, nullable=False, default=0.0)
    patient_payable = Column(Float, nullable=False, default=0.0)
    payment_status = Column(String(32), nullable=False, default="draft")  # draft, pending, paid, partially_paid, cancelled
    items_json = Column(Text, nullable=False, default="[]")  # Line items: bed, consultations, tests, procedures, drugs
    icd10_codes_json = Column(Text, nullable=False, default="[]")  # Assisted ICD-10 codes
    coded_by = Column(String(64), default="billing_rcm_agent", nullable=False)
    approved_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient")


class AgentEventLog(Base):
    __tablename__ = "agent_events"

    event_id = Column(String(64), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source_agent = Column(String(64), nullable=False, index=True)  # intake, scheduling, lab_pharmacy, procurement, billing_rcm, bi
    target_agent = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="completed")  # emitted, in_progress, completed, failed, escalated
    requires_human_approval = Column(Boolean, default=False, nullable=False)
    approval_status = Column(String(32), nullable=True)  # pending, approved, rejected
    resolution_notes = Column(Text, nullable=True)


# ============================================================================
# EXTENDED HMS MODELS: FAMILY ACCOUNTS, CLINICAL WORKSPACE & NURSING WORKSPACE
# ============================================================================

class FamilyLink(Base):
    """
    Patient-to-Patient Family Account Linking & Consent-Based Access Control.
    Enforces that name discovery alone never grants access; explicit target approval is required.
    """
    __tablename__ = "family_links"

    link_id = Column(String(64), primary_key=True)
    requester_patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    target_patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(64), nullable=False)  # spouse, parent, child, sibling, guardian, other
    status = Column(String(32), default="pending", nullable=False, index=True)  # pending, approved, rejected, revoked
    permissions_json = Column(Text, default="[]", nullable=False)  # JSON list of permissions: view_basic_health, view_medical_history, view_reports, manage_appointments, receive_reminders, assist_admissions, access_documents
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    responded_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    requester = relationship("Patient", foreign_keys=[requester_patient_id])
    target = relationship("Patient", foreign_keys=[target_patient_id])

    __table_args__ = (
        UniqueConstraint("requester_patient_id", "target_patient_id", name="uq_patient_family_link"),
    )


class ClinicalNote(Base):
    """
    Physician Documentation: Consultation notes, SOAP notes, progress notes,
    discharge summaries, treatment plans, and clinical referrals.
    """
    __tablename__ = "clinical_notes"

    note_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_id = Column(String(64), ForeignKey("encounters.encounter_id", ondelete="SET NULL"), nullable=True, index=True)
    doctor_id = Column(String(64), nullable=False, index=True)
    doctor_name = Column(String(150), nullable=False)
    note_type = Column(String(64), default="progress_note", nullable=False, index=True)  # consultation, progress_note, soap_note, discharge_summary, treatment_plan, referral
    title = Column(String(200), nullable=False)
    subjective = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)
    assessment = Column(Text, nullable=True)
    plan = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("Patient")
    encounter = relationship("Encounter")


class ClinicalOrder(Base):
    """
    Physician Diagnostic & Procedure Orders: Laboratory investigations,
    imaging studies (X-Ray, MRI, CT), and nursing interventions.
    """
    __tablename__ = "clinical_orders"

    order_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_id = Column(String(64), ForeignKey("encounters.encounter_id", ondelete="SET NULL"), nullable=True, index=True)
    doctor_id = Column(String(64), nullable=False, index=True)
    doctor_name = Column(String(150), nullable=False)
    order_type = Column(String(64), nullable=False, index=True)  # lab, imaging, procedure, nursing_intervention
    order_name = Column(String(200), nullable=False)
    clinical_indication = Column(Text, nullable=True)
    priority = Column(String(32), default="routine", nullable=False)  # routine, urgent, stat
    status = Column(String(32), default="ordered", nullable=False, index=True)  # ordered, sample_collected, in_progress, completed, cancelled
    result_summary = Column(Text, nullable=True)
    ordered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)

    patient = relationship("Patient")
    encounter = relationship("Encounter")


class NursingTask(Base):
    """
    Nurse Task Management: Medication rounds, vitals recording, lab sample collection,
    procedure prep, wound care, doctor instructions, and admission/discharge workflows.
    """
    __tablename__ = "nursing_tasks"

    task_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_id = Column(String(64), ForeignKey("encounters.encounter_id", ondelete="SET NULL"), nullable=True)
    ward = Column(String(64), nullable=False, index=True)
    bed_number = Column(String(32), nullable=True)
    task_type = Column(String(64), nullable=False, index=True)  # medication, vitals, lab_collection, wound_care, procedure_prep, doctor_order, admission_discharge
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(32), default="routine", nullable=False)  # routine, urgent, stat
    scheduled_time = Column(DateTime, nullable=False, index=True)
    status = Column(String(32), default="pending", nullable=False, index=True)  # pending, in_progress, completed, overdue, cancelled
    assigned_nurse_id = Column(String(64), nullable=True, index=True)
    assigned_nurse_name = Column(String(150), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String(150), nullable=True)
    completion_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient")


class MedicationAdministration(Base):
    """
    Medication Administration Record (MAR): Track prescribed medicine, scheduled timing,
    actual administration status (administered, delayed, refused, missed with reason), and nurse verification.
    """
    __tablename__ = "medication_administrations"

    mar_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    medication_id = Column(String(64), ForeignKey("medications.medication_id", ondelete="SET NULL"), nullable=True)
    medication_name = Column(String(200), nullable=False)
    dosage = Column(String(100), nullable=False)
    route = Column(String(64), nullable=False, default="oral")  # oral, iv, im, sc, topical, inhalation
    scheduled_time = Column(DateTime, nullable=False, index=True)
    administered_time = Column(DateTime, nullable=True)
    administered_by = Column(String(150), nullable=True)  # Nurse name/ID
    status = Column(String(32), default="scheduled", nullable=False, index=True)  # scheduled, administered, delayed, refused, missed
    reason = Column(Text, nullable=True)  # Reason for delay, refusal, or omission
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient")
    medication = relationship("Medication")


class ShiftHandover(Base):
    """
    Clinical Communication & Shift Handover: Structured SBAR format
    (Situation, Background, Assessment, Recommendation) with critical alerts and task handoffs.
    """
    __tablename__ = "shift_handovers"

    handover_id = Column(String(64), primary_key=True)
    ward = Column(String(64), nullable=False, index=True)
    shift_type = Column(String(32), nullable=False)  # morning, evening, night
    outgoing_nurse_id = Column(String(64), nullable=False)
    outgoing_nurse_name = Column(String(150), nullable=False)
    incoming_nurse_id = Column(String(64), nullable=True)
    incoming_nurse_name = Column(String(150), nullable=True)
    handover_date = Column(Date, nullable=False, default=date.today)
    situation = Column(Text, nullable=False)
    background = Column(Text, nullable=False)
    assessment = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    critical_alerts_json = Column(Text, default="[]", nullable=False)
    total_patients = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CareTeamAssignment(Base):
    """
    Care Team Assignments: Doctor-patient and nurse-patient clinical coverage.
    """
    __tablename__ = "care_team_assignments"

    assignment_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    staff_user_id = Column(String(64), nullable=False, index=True)
    staff_name = Column(String(150), nullable=False)
    staff_role = Column(String(32), nullable=False)  # doctor, nurse
    department = Column(String(100), nullable=False)
    is_primary = Column(Boolean, default=True, nullable=False)
    assigned_date = Column(Date, nullable=False, default=date.today)
    status = Column(String(32), default="active", nullable=False)  # active, completed, transferred
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient")




