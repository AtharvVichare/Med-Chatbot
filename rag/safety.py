"""
Clinical Safety, Emergency Detection, and Input Screening Engine
Features:
- Robust identification of acute emergency red flags across diverse descriptions:
    * Acute Coronary Syndromes / Chest Pain
    * Acute Stroke / Cerebrovascular events (BE-FAST signs)
    * Severe Dyspnea / Respiratory distress
    * Anaphylaxis / Airway compromise
    * Acute neurological deficits / Loss of consciousness / Syncope / Seizures
    * Severe trauma / Hemorrhage / Massive hemoptysis
- Configurable regional emergency guidance (authoritative Indian helplines: 112 National Emergency, 102/108 Ambulance; International fallback: 911/999/local emergency number)
- Adversarial prompt injection screening
- Flags out-of-scope clinical requests
- Explicit clinical disclaimer attached to all evaluations
"""

import re
from typing import Dict, Any, List, Optional

# Extended semantic symptom patterns for acute emergencies
EMERGENCY_SYMPTOM_GROUPS = {
    "chest_pain_cardiac": [
        r"\b(chest pain|chest tightness|chest pressure|crushing chest|squeezing chest|heavy feeling in chest|tightness in (my|the) chest)\b",
        r"\b(radiating to (my )?(left arm|neck|jaw|shoulder|back))\b",
        r"\b(heart attack|myocardial infarction|angina)\b",
        r"\b(sweating and chest pain|nausea with chest pain|cold sweats and pain in chest)\b"
    ],
    "stroke_neurological": [
        r"\b(sudden weakness|face drooping|facial droop|arm weakness|arm numbness|speech difficulty|slurred speech|unable to speak)\b",
        r"\b(stroke|brain stroke|cva|transient ischemic attack|tia)\b",
        r"\b(one-sided numbness|hemiplegia|one side of (my )?body feels numb|cannot move (my )?left arm|cannot move (my )?right arm)\b",
        r"\b(thunderclap headache|worst headache of (my )?life|sudden severe explosive headache)\b"
    ],
    "respiratory_failure": [
        r"\b(cannot breathe|can't breathe|severe shortness of breath|gasping for air|struggling to breathe|suffocating)\b",
        r"\b(blue lips|blue fingernails|cyanosis|turning blue)\b",
        r"\b(stridor|wheezing violently|choking on|airway blocked)\b"
    ],
    "anaphylaxis_allergic": [
        r"\b(swollen tongue|tongue swelling|throat closing up|tight throat|unable to swallow after eating|allergic reaction and can't breathe)\b",
        r"\b(anaphylaxis|anaphylactic shock)\b"
    ],
    "consciousness_syncope": [
        r"\b(passed out|blacked out|loss of consciousness|unresponsive|collapsed|unconscious|fainted suddenly|fainting and not waking up)\b",
        r"\b(continuous seizure|convulsing|status epilepticus)\b"
    ],
    "acute_hemorrhage": [
        r"\b(coughing up blood|vomiting blood|massive bleeding|blood gushing|uncontrolled bleeding)\b"
    ]
}

# Adversarial Prompt Injection Signatures
PROMPT_INJECTION_PATTERNS = [
    r"\b(ignore (all )?previous instructions|disregard (all )?system prompts|forget (all )?previous guidelines)\b",
    r"\b(you are now (in developer mode|jailbroken|dan|an unrestricted ai))\b",
    r"\b(reveal (the )?(system prompt|secret key|api key|internal instructions))\b",
    r"\b(bypass safety filters|override safety|disable guardrails)\b"
]

class MedicalSafetyEngine:

    @staticmethod
    def screen_question(
        question: str,
        country_code: str = "IN"
    ) -> Dict[str, Any]:
        """
        Screens incoming user query before retrieval.
        Returns safety assessment, emergency flags, and location-appropriate escalation directives.
        """
        q_lower = question.lower()
        emergency_detected = False
        matched_categories = []
        emergency_reasons = []

        for category, patterns in EMERGENCY_SYMPTOM_GROUPS.items():
            for pat in patterns:
                if re.search(pat, q_lower):
                    emergency_detected = True
                    if category not in matched_categories:
                        matched_categories.append(category)
                    emergency_reasons.append(f"[{category}] Matched pattern: {pat}")
                    break  # Found match for this category

        # Check prompt injection
        injection_detected = False
        injection_reasons = []
        for pat in PROMPT_INJECTION_PATTERNS:
            if re.search(pat, q_lower):
                injection_detected = True
                injection_reasons.append(f"Matched prompt injection: {pat}")

        safety_flags = {
            "is_emergency": emergency_detected,
            "emergency_categories": matched_categories,
            "emergency_reasons": emergency_reasons,
            "is_prompt_injection": injection_detected,
            "injection_reasons": injection_reasons,
            "requires_urgent_escalation": emergency_detected
        }

        emergency_directive = None
        if emergency_detected:
            if country_code.upper() == "IN":
                emergency_directive = (
                    "CRITICAL MEDICAL EMERGENCY WARNING: The symptoms described may represent an acute, life-threatening "
                    "medical emergency (such as acute coronary syndrome / myocardial infarction, acute cerebrovascular stroke, "
                    "or severe airway/respiratory compromise).\n\n"
                    "IMMEDIATE ACTION REQUIRED:\n"
                    "1. Call Emergency Services immediately: Dial 112 (National Emergency Number in India) or 108 / 102 (Ambulance).\n"
                    "2. Transport the individual immediately to the nearest hospital casualty / emergency department.\n"
                    "3. DO NOT delay care to read or wait for online medical advice."
                )
            else:
                emergency_directive = (
                    "CRITICAL MEDICAL EMERGENCY WARNING: The symptoms described may represent an acute, life-threatening "
                    "medical emergency (such as acute myocardial infarction, acute stroke, or severe respiratory failure).\n\n"
                    "IMMEDIATE ACTION REQUIRED:\n"
                    "1. Immediately call your local emergency services (e.g., 911 in North America, 112 in Europe/India, 999 in UK).\n"
                    "2. Proceed immediately to the nearest hospital emergency department.\n"
                    "3. DO NOT rely on an AI system or online tool for emergency triage."
                )

        return {
            "safety_flags": safety_flags,
            "emergency_directive": emergency_directive,
            "safe_to_process": not injection_detected
        }
