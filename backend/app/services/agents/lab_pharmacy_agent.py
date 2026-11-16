"""
Lab & Pharmacy Agent for Aarogya-Drishti HMS.
Manages:
- Processing lab orders & reports
- Drug-drug interaction safety checks
- Patient allergy cross-checking
- Clinical decision escalation for dangerous combinations
"""

import re
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.models import Medication, Allergy, Patient
from backend.app.services.agent_event_bus import AgentEventBus

logger = logging.getLogger("LabPharmacyAgent")

# Known high-risk clinical drug interactions
DRUG_INTERACTIONS = [
    {
        "drug_a": "warfarin",
        "drug_b": "aspirin",
        "severity": "critical",
        "effect": "Severe risk of major bleeding and gastrointestinal hemorrhage. Concurrent antiplatelet and anticoagulant therapy requires strict INR monitoring."
    },
    {
        "drug_a": "warfarin",
        "drug_b": "ibuprofen",
        "severity": "critical",
        "effect": "NSAIDs dramatically increase the risk of serious GI bleeding and inhibit platelet aggregation in patients on Warfarin."
    },
    {
        "drug_a": "clopidogrel",
        "drug_b": "omeprazole",
        "severity": "major",
        "effect": "Omeprazole significantly reduces the antiplatelet metabolic activation of Clopidogrel via CYP2C19 inhibition."
    },
    {
        "drug_a": "lisinopril",
        "drug_b": "spironolactone",
        "severity": "major",
        "effect": "Potent additive risk of life-threatening severe hyperkalemia. Concurrent use requires frequent serum potassium monitoring."
    },
    {
        "drug_a": "metformin",
        "drug_b": "iodinated contrast",
        "severity": "critical",
        "effect": "Risk of contrast-induced nephropathy leading to acute renal failure and fatal lactic acidosis. Metformin must be held 48 hours prior."
    },
    {
        "drug_a": "atorvastatin",
        "drug_b": "clarithromycin",
        "severity": "major",
        "effect": "Strong CYP3A4 inhibition elevates serum Atorvastatin levels exponentially, increasing the danger of rhabdomyolysis."
    },
    {
        "drug_a": "tramadol",
        "drug_b": "sertraline",
        "severity": "critical",
        "effect": "Risk of Serotonin Syndrome and lowered seizure threshold due to combined serotonergic agonism."
    },
    {
        "drug_a": "amoxicillin",
        "drug_b": "methotrexate",
        "severity": "major",
        "effect": "Penicillins reduce renal tubular clearance of Methotrexate, creating severe bone marrow toxicity risk."
    }
]

class LabPharmacyAgent:
    @staticmethod
    def check_drug_safety(
        proposed_medication: str,
        patient_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Performs thorough safety verification for a proposed drug against:
        1. Current active medications in patient EHR
        2. Known patient allergies
        """
        proposed_clean = proposed_medication.lower()

        # 1. Fetch active medications
        active_meds = db.scalars(
            select(Medication).where(
                Medication.patient_id == patient_id,
                Medication.status == "active"
            )
        ).all()

        interactions_detected = []
        for med in active_meds:
            curr_med_clean = med.medication_name.lower()
            for pair in DRUG_INTERACTIONS:
                a, b = pair["drug_a"], pair["drug_b"]
                if (a in proposed_clean and b in curr_med_clean) or (b in proposed_clean and a in curr_med_clean):
                    interactions_detected.append({
                        "existing_drug": med.medication_name,
                        "proposed_drug": proposed_medication,
                        "severity": pair["severity"],
                        "clinical_effect": pair["effect"]
                    })

        # 2. Fetch allergies
        allergies = db.scalars(
            select(Allergy).where(Allergy.patient_id == patient_id)
        ).all()

        allergy_alerts = []
        for alg in allergies:
            substance = alg.substance.lower()
            if substance in proposed_clean or any(k in proposed_clean for k in substance.split()):
                allergy_alerts.append({
                    "substance": alg.substance,
                    "reaction": alg.reaction,
                    "severity": alg.severity
                })

        is_safe = len(interactions_detected) == 0 and len(allergy_alerts) == 0
        severity_level = "safe"
        if any(i["severity"] == "critical" for i in interactions_detected) or any(a["severity"] == "life-threatening" for a in allergy_alerts):
            severity_level = "critical"
        elif interactions_detected or allergy_alerts:
            severity_level = "warning"

        # Emit event if warnings exist
        if not is_safe:
            AgentEventBus.emit(
                source_agent="lab_pharmacy_agent",
                event_type="MEDICATION_SAFETY_ALERT",
                payload={
                    "patient_id": patient_id,
                    "proposed_medication": proposed_medication,
                    "severity": severity_level,
                    "interactions": interactions_detected,
                    "allergy_conflicts": allergy_alerts
                },
                target_agent="doctor_dashboard",
                requires_human_approval=True,
                db=db
            )

        return {
            "is_safe": is_safe,
            "severity_level": severity_level,
            "proposed_medication": proposed_medication,
            "drug_interactions": interactions_detected,
            "allergy_conflicts": allergy_alerts,
            "recommendation": (
                "Medication cleared with zero detected adverse interactions."
                if is_safe else
                f"SAFETY WARNING: High risk clinical interaction or allergy flagged ({severity_level.upper()}). Physician review required."
            )
        }
