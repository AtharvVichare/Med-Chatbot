"""
Intake Agent for Aarogya-Drishti HMS.
Understands patient inquiries via text, voice, or file uploads.
Collects symptoms, performs triage, recommends medical specialties,
and initiates appointment bookings or admission requests.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.services.agents.scheduling_agent import SchedulingAgent
from backend.app.services.agent_event_bus import AgentEventBus
from backend.app.db.models import DoctorProfile, BedRegistry, Patient

logger = logging.getLogger("IntakeAgent")

SPECIALTY_MAPPINGS = {
    "cardiology": ["chest pain", "angina", "heart", "palpitation", "high bp", "hypertension", "cardiac", "shortness of breath on walking"],
    "general medicine": ["fever", "diabetes", "sugar", "weakness", "vomiting", "diarrhea", "infection", "head cold", "chills", "fatigue"],
    "neurology": ["headache", "migraine", "dizziness", "vertigo", "seizure", "numbness", "tingling", "tremor", "stroke"],
    "orthopedics": ["bone", "joint", "knee", "back pain", "spine", "fracture", "arthritis", "shoulder", "ligament"],
    "pediatrics": ["child", "baby", "infant", "pediatric", "vaccine", "colic", "toddler"],
    "pulmonology": ["cough", "asthma", "wheezing", "breathlessness", "lungs", "copd", "phlegm", "chest congestion"],
    "obstetrics & gynecology": ["pregnancy", "maternity", "period", "menstrual", "pelvic", "gynec", "contraceptive", "ultrasound fetal"],
    "nephrology": ["kidney", "renal", "swelling feet", "edema", "dialysis", "creatinine", "urine pain"],
    "oncology": ["cancer", "tumor", "chemo", "chemotherapy", "oncology", "malignancy", "radiation", "biopsy", "mass"]
}

class IntakeAgent:
    @staticmethod
    def triage_symptoms(query: str) -> Dict[str, Any]:
        """Analyzes symptoms to identify the most appropriate clinical specialty and urgency."""
        q_low = query.lower()
        matched_specialties = []

        for dept, keywords in SPECIALTY_MAPPINGS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', q_low):
                    matched_specialties.append(dept)
                    break

        recommended_dept = matched_specialties[0].title() if matched_specialties else "General Medicine"

        # Determine priority/urgency
        is_emergency = any(k in q_low for k in ["severe chest pain", "unconscious", "heavy bleeding", "unable to breathe", "severe trauma", "stroke"])
        is_urgent = any(k in q_low for k in ["high fever", "acute pain", "vomiting blood", "fracture", "urgent"])

        priority = "emergency" if is_emergency else ("urgent" if is_urgent else "routine")

        return {
            "recommended_department": recommended_dept,
            "matched_specialties": matched_specialties,
            "priority": priority,
            "is_emergency": is_emergency,
            "requires_admission": is_emergency or "admit" in q_low or "hospital bed" in q_low or "admission" in q_low
        }

    @staticmethod
    def process_patient_request(
        message: str,
        patient_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Processes natural language query from patient, triages symptoms,
        and prepares booking or admission actions.
        """
        triage = IntakeAgent.triage_symptoms(message)
        dept = triage["recommended_department"]
        priority = triage["priority"]

        # Check for admission intent
        if triage["requires_admission"]:
            ward_pref = "ICU" if priority == "emergency" else ("Emergency" if priority == "urgent" else "General Male")
            bed_info = SchedulingAgent.find_available_bed(ward=ward_pref, db=db)
            available_beds_count = 1 if bed_info else 0

            return {
                "action_type": "admission_recommendation",
                "department": dept,
                "priority": priority,
                "recommended_ward": ward_pref,
                "available_bed": bed_info.bed_number if bed_info else None,
                "daily_charge": bed_info.daily_charge if bed_info else None,
                "message": (
                    f"Based on your symptoms, we recommend an admission evaluation under **{dept}** (Priority: **{priority.upper()}**). "
                    + (f"Bed **{bed_info.bed_number}** in the **{ward_pref}** ward is currently available." if bed_info else f"All beds in {ward_pref} are currently occupied; our triage team has been alerted for priority waitlisting.")
                )
            }

        # Otherwise consultation appointment booking flow
        doctors = SchedulingAgent.get_available_doctors(department=dept, db=db)
        if not doctors:
            # Fallback to general medicine
            doctors = SchedulingAgent.get_available_doctors(department="General Medicine", db=db)

        # Emit intake triage event
        AgentEventBus.emit(
            source_agent="intake_agent",
            event_type="PATIENT_INTAKE_TRIAGED",
            payload={
                "patient_id": patient_id,
                "message": message,
                "department": dept,
                "priority": priority,
                "doctors_found": len(doctors)
            },
            target_agent="scheduling_agent",
            requires_human_approval=False,
            db=db
        )

        return {
            "action_type": "doctor_recommendation",
            "department": dept,
            "priority": priority,
            "doctors": doctors,
            "suggested_date": str(date.today() + timedelta(days=1)),
            "message": (
                f"Based on your symptoms, I recommend a consultation with our **{dept}** department. "
                f"We have verified specialist doctors available across top partner tertiary hospitals. "
                f"Please choose your preferred consultant and consultation slot below:"
            )
        }
