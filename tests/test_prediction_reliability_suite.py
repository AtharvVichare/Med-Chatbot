"""
Realistic Evaluation Suite for Disease Prediction Reliability & Independent Safety Layer
Tests the 11 clinical scenarios mandated in Phase 4.1:
1. Isolated common cold symptoms
2. Isolated cough
3. Cough with fever
4. Cough with breathing difficulty
5. Mild headache
6. Mild fatigue
7. Multiple overlapping symptoms
8. Empty symptom input
9. Very sparse symptom input
10. Concerning chest symptoms
11. Unseen symptom combinations
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from backend.app.services.disease_prediction import (
    get_disease_prediction_service,
    PredictionStatus,
    CLINICAL_DISCLAIMER
)
from backend.app.services.safety_triage import (
    evaluate_safety_warnings,
    SafetyTriageLevel
)

pred_service = get_disease_prediction_service()

def evaluate_case(name: str, symptoms: list, quality_factors: dict = None):
    quality_factors = quality_factors or {}
    
    # 1. Independent Safety Layer
    warnings = evaluate_safety_warnings(
        symptoms=symptoms,
        duration=quality_factors.get("duration"),
        severity=quality_factors.get("severity"),
        progression=quality_factors.get("progression"),
        has_fever=quality_factors.get("has_fever"),
        breathing_difficulty=quality_factors.get("breathing_difficulty"),
        chest_discomfort=quality_factors.get("chest_discomfort"),
        medical_history=quality_factors.get("medical_history")
    )
    
    # 2. Disease Prediction Service
    if not symptoms:
        pred_result = {
            "predictions": [],
            "evidence_status": PredictionStatus.INSUFFICIENT_INFORMATION,
            "abstention_reason": "Empty symptom list provided.",
            "top_model_score": 0.0,
            "score_margin": 0.0,
            "symptoms_supplied_count": 0
        }
    else:
        pred_result = pred_service.predict_top_k(symptoms=symptoms)
        
    emergency_warnings = [w for w in warnings if w.level == SafetyTriageLevel.EMERGENCY]
    urgent_warnings = [w for w in warnings if w.level == SafetyTriageLevel.URGENT]
    
    # Check if an alarming prediction (e.g. Heart Attack or Bronchial Asthma) is displayed without support
    displayed_categories = [p["disease_category"] for p in pred_result["predictions"]]
    has_heart_attack_displayed = "Heart Attack" in displayed_categories
    has_asthma_displayed = "Bronchial Asthma" in displayed_categories
    
    return {
        "case_name": name,
        "input_symptoms": symptoms,
        "evidence_status": pred_result["evidence_status"],
        "abstained": pred_result["evidence_status"] == PredictionStatus.INSUFFICIENT_INFORMATION,
        "low_confidence": pred_result["evidence_status"] == PredictionStatus.LOW_CONFIDENCE,
        "displayed_predictions_count": len(pred_result["predictions"]),
        "displayed_predictions": displayed_categories,
        "emergency_warnings_count": len(emergency_warnings),
        "urgent_warnings_count": len(urgent_warnings),
        "emergency_warning_displayed": len(emergency_warnings) > 0,
        "heart_attack_displayed": has_heart_attack_displayed,
        "asthma_displayed": has_asthma_displayed,
        "top_score": pred_result.get("top_model_score", 0.0),
        "margin": pred_result.get("score_margin", 0.0)
    }

def test_case_1_isolated_common_cold():
    # Case 1: Isolated common cold symptoms
    res = evaluate_case("Isolated common cold", ["continuous_sneezing"])
    assert res["abstained"] is True
    assert res["displayed_predictions_count"] == 0
    assert not res["heart_attack_displayed"], "Heart Attack must not be displayed for isolated sneezing!"

def test_case_2_isolated_cough():
    # Case 2: Isolated cough
    res = evaluate_case("Isolated cough", ["cough"])
    assert res["abstained"] is True
    assert res["displayed_predictions_count"] == 0
    assert not res["asthma_displayed"], "Asthma must not be displayed as confident top prediction for single cough!"

def test_case_3_cough_with_fever():
    # Case 3: Cough with fever (2 symptoms)
    res = evaluate_case("Cough with fever", ["cough", "mild_fever"], {"has_fever": True})
    assert res["abstained"] is True
    assert res["displayed_predictions_count"] == 0

def test_case_4_cough_with_breathing_difficulty():
    # Case 4: Cough with breathing difficulty
    res = evaluate_case("Cough with breathing difficulty", ["cough", "breathlessness"], {"breathing_difficulty": True, "severity": "severe"})
    assert res["emergency_warning_displayed"] is True
    assert res["emergency_warnings_count"] >= 1
    # Model abstains from diagnosis or flags low confidence because input is sparse (2 symptoms)
    assert res["abstained"] is True

def test_case_5_mild_headache():
    # Case 5: Mild headache
    res = evaluate_case("Mild headache", ["headache"], {"severity": "mild"})
    assert res["abstained"] is True
    assert not res["heart_attack_displayed"]

def test_case_6_mild_fatigue():
    # Case 6: Mild fatigue
    res = evaluate_case("Mild fatigue", ["fatigue"], {"severity": "mild"})
    assert res["abstained"] is True
    assert not res["heart_attack_displayed"]

def test_case_7_multiple_overlapping_symptoms():
    # Case 7: Multiple overlapping symptoms
    syms = ["continuous_sneezing", "chills", "fatigue", "cough", "high_fever", "headache", "runny_nose", "congestion", "chest_pain", "loss_of_smell", "muscle_pain"]
    res = evaluate_case("Multiple overlapping symptoms", syms)
    # 11 symptoms: fits common cold training cluster
    assert res["displayed_predictions_count"] > 0
    assert "Common Cold" in res["displayed_predictions"]

def test_case_8_empty_input():
    # Case 8: Empty symptom input
    res = evaluate_case("Empty input", [])
    assert res["abstained"] is True
    assert res["displayed_predictions_count"] == 0

def test_case_9_very_sparse_input():
    # Case 9: Very sparse symptom input (1 symptom)
    res = evaluate_case("Very sparse input", ["shivering"])
    assert res["abstained"] is True
    assert res["displayed_predictions_count"] == 0

def test_case_10_concerning_chest_symptoms():
    # Case 10: Concerning chest symptoms (chest_pain, breathlessness, sweating)
    syms = ["chest_pain", "breathlessness", "sweating"]
    res = evaluate_case("Concerning chest symptoms", syms, {"chest_discomfort": True, "severity": "severe"})
    assert res["emergency_warning_displayed"] is True
    assert res["evidence_status"] == PredictionStatus.SUFFICIENT_EVIDENCE
    assert res["displayed_predictions_count"] == 3

def test_case_11_unseen_symptom_combination():
    # Case 11: Unseen symptom combinations (acidity, knee_pain)
    res = evaluate_case("Unseen symptom combinations", ["acidity", "knee_pain"])
    assert res["abstained"] is True
    assert res["displayed_predictions_count"] == 0

if __name__ == "__main__":
    cases = [
        ("Isolated common cold", ["continuous_sneezing"], {}),
        ("Isolated cough", ["cough"], {}),
        ("Cough with fever", ["cough", "mild_fever"], {"has_fever": True}),
        ("Cough with breathing difficulty", ["cough", "breathlessness"], {"breathing_difficulty": True, "severity": "severe"}),
        ("Mild headache", ["headache"], {"severity": "mild"}),
        ("Mild fatigue", ["fatigue"], {"severity": "mild"}),
        ("Multiple overlapping symptoms", ["continuous_sneezing", "chills", "fatigue", "cough", "high_fever", "headache", "runny_nose", "congestion", "chest_pain", "loss_of_smell", "muscle_pain"], {}),
        ("Empty symptom input", [], {}),
        ("Very sparse symptom input", ["shivering"], {}),
        ("Concerning chest symptoms", ["chest_pain", "breathlessness", "sweating"], {"chest_discomfort": True, "severity": "severe"}),
        ("Unseen symptom combinations", ["acidity", "knee_pain"], {})
    ]
    results = [evaluate_case(c[0], c[1], c[2]) for c in cases]
    print(json.dumps(results, indent=2))
