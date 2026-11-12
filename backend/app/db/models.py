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


class Encounter(Base):
    __tablename__ = "encounters"

    encounter_id = Column(String(64), primary_key=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_date = Column(Date, nullable=False, index=True)
    facility = Column(String(200), nullable=False)
    district = Column(String(100), nullable=False)
    encounter_type = Column(String(64), nullable=False)
    attending_provider = Column(String(150), nullable=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="encounters")
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


