"""
Independent Medical Safety Warning Evaluation Layer
Provides rule-based, deterministic clinical safety risk triaging that operates completely
independently of the experimental ML disease classifier.

Safety Principles:
1. Operates independently of disease classification predictions.
2. Emergency warnings ALWAYS take priority over ML predictions.
3. Does NOT diagnose medical conditions (e.g. does not diagnose 'myocardial infarction' or 'status asthmaticus').
4. Never reassures a user that an emergency is absent simply because the ML model did not predict it.
5. Does not treat absence of a symptom as proof of safety.
6. Displays emergency medical guidance including India's emergency helpline (112).
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class SafetyTriageLevel(str, Enum):
    EMERGENCY = "EMERGENCY"         # Immediate emergency care / ambulance required (e.g. Call 112)
    URGENT = "URGENT"               # Prompt clinical evaluation required (same-day or urgent care)
    ROUTINE = "ROUTINE"             # Standard clinical consultation / primary care evaluation
    INFORMATIONAL = "INFORMATIONAL" # Non-urgent educational guidance

class SafetyWarning(BaseModel):
    level: SafetyTriageLevel = Field(..., description="Triage urgency level")
    title: str = Field(..., description="Short title of the safety advisory")
    message: str = Field(..., description="Actionable clinical guidance message")
    emergency_action_recommended: bool = Field(False, description="Whether immediate emergency action (e.g. call 112) is needed")
    triggers: List[str] = Field(default_factory=list, description="Symptom or contextual triggers that generated this warning")

def evaluate_safety_warnings(
    symptoms: List[str],
    duration: Optional[str] = None,
    severity: Optional[str] = None,
    progression: Optional[str] = None,
    has_fever: Optional[bool] = None,
    breathing_difficulty: Optional[bool] = None,
    chest_discomfort: Optional[bool] = None,
    medical_history: Optional[List[str]] = None
) -> List[SafetyWarning]:
    """
    Evaluates symptoms and optional contextual quality factors to produce independent safety advisories.
    """
    warnings: List[SafetyWarning] = []
    sym_set = set(s.strip().lower() for s in (symptoms or []))
    history_set = set(h.strip().lower() for h in (medical_history or []))

    # --- 1. RED FLAG: Severe Breathing Difficulty / Respiratory Distress ---
    severe_respiratory = (
        breathing_difficulty is True
        or "breathlessness" in sym_set
    )
    if severe_respiratory:
        # Check compounding red flags
        is_severe = (
            severity in ["severe", "critical"]
            or "cough" in sym_set
            or has_fever is True
            or "high_fever" in sym_set
            or chest_discomfort is True
            or "chest_pain" in sym_set
        )
        if is_severe:
            warnings.append(SafetyWarning(
                level=SafetyTriageLevel.EMERGENCY,
                title="Immediate Emergency Evaluation Needed: Respiratory Distress",
                message=(
                    "Severe breathing difficulty, particularly when accompanied by chest discomfort, fever, or rapid progression, "
                    "can be a medical emergency. Seek immediate emergency medical care or call national emergency services (112 in India)."
                ),
                emergency_action_recommended=True,
                triggers=[s for s in ["breathlessness", "breathing_difficulty", "chest_pain", "high_fever"] if s in sym_set or (s == "breathing_difficulty" and breathing_difficulty)]
            ))
        else:
            warnings.append(SafetyWarning(
                level=SafetyTriageLevel.URGENT,
                title="Urgent Clinical Evaluation Recommended: Shortness of Breath",
                message=(
                    "Difficulty breathing or breathlessness requires timely evaluation by a qualified medical provider. "
                    "If breathing difficulty worsens suddenly, causes inability to speak in full sentences, or is accompanied by chest tightness, "
                    "seek emergency care immediately."
                ),
                emergency_action_recommended=False,
                triggers=["breathlessness"]
            ))

    # --- 2. RED FLAG: Concerning Chest Symptoms / Acute Coronary Syndrome Risk ---
    acute_chest = (
        chest_discomfort is True
        or "chest_pain" in sym_set
    )
    if acute_chest:
        has_cardiac_correlates = (
            "sweating" in sym_set
            or "breathlessness" in sym_set
            or breathing_difficulty is True
            or "nausea" in sym_set
            or "vomiting" in sym_set
            or "dizziness" in sym_set
            or severity in ["severe", "critical"]
            or any("cardiac" in h or "heart" in h or "hypertension" in h for h in history_set)
        )
        if has_cardiac_correlates:
            warnings.append(SafetyWarning(
                level=SafetyTriageLevel.EMERGENCY,
                title="Immediate Emergency Medical Attention Required: Concerning Chest Discomfort",
                message=(
                    "New, worsening, or persistent chest discomfort, especially when associated with sweating, shortness of breath, "
                    "nausea, lightheadedness, or radiation to the neck, jaw, or arms, is a potential medical emergency. "
                    "Do NOT wait or rely on symptom predictions. Call emergency services immediately (112 in India) or go to the nearest emergency department."
                ),
                emergency_action_recommended=True,
                triggers=[s for s in ["chest_pain", "sweating", "breathlessness", "nausea", "vomiting", "dizziness"] if s in sym_set or (s == "chest_pain" and chest_discomfort)]
            ))
        else:
            warnings.append(SafetyWarning(
                level=SafetyTriageLevel.URGENT,
                title="Urgent Evaluation Recommended: Unexplained Chest Discomfort",
                message=(
                    "Any unexplained chest pain or discomfort warrants prompt physical evaluation and an ECG by a physician to rule out cardiac and pulmonary causes. "
                    "Seek immediate emergency care if discomfort spreads, intensifies, or is accompanied by sweating or shortness of breath."
                ),
                emergency_action_recommended=False,
                triggers=["chest_pain"]
            ))

    # --- 3. RED FLAG: Neurological Warning Signs ---
    neuro_signs = [s for s in ["altered_sensorium", "weakness_of_one_body_side", "slurred_speech", "loss_of_balance", "coma"] if s in sym_set]
    if neuro_signs:
        warnings.append(SafetyWarning(
            level=SafetyTriageLevel.EMERGENCY,
            title="Immediate Emergency Evaluation Required: Acute Neurological Signs",
            message=(
                "Symptoms such as unilateral weakness, slurred speech, confusion, or altered consciousness may indicate an acute cerebrovascular event. "
                "Immediate emergency clinical care (call 112 in India) is vital."
            ),
            emergency_action_recommended=True,
            triggers=neuro_signs
        ))

    # --- 4. High / Persistent Fever with Red Flags ---
    fever_present = has_fever is True or "high_fever" in sym_set or "mild_fever" in sym_set
    if fever_present and (progression == "worsening" or duration in ["> 1 week", "> 2 weeks"] or "altered_sensorium" in sym_set):
        warnings.append(SafetyWarning(
            level=SafetyTriageLevel.URGENT,
            title="Urgent Clinical Review: Prolonged or Worsening Febrile Illness",
            message=(
                "Fever that is worsening or persisting over an extended duration requires medical workup to evaluate for underlying systemic infections. "
                "Consult a physician for laboratory testing."
            ),
            emergency_action_recommended=False,
            triggers=["fever_progression"]
        ))

    # Sort so EMERGENCY always comes first, followed by URGENT
    order = {SafetyTriageLevel.EMERGENCY: 0, SafetyTriageLevel.URGENT: 1, SafetyTriageLevel.ROUTINE: 2, SafetyTriageLevel.INFORMATIONAL: 3}
    warnings.sort(key=lambda w: order[w.level])
    return warnings

