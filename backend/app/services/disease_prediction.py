"""
Disease Prediction Model Service
Manages lifecycle of the trained symptom-based disease classification pipeline:
- Loads the serialized joblib artifact and metadata once upon initialization.
- Validates the artifact against metadata (132 exact symptom features, 41 classes).
- Converts input symptom checklists into exact 132-element binary vectors in saved feature order.
- Computes Top-3 ranked differential predictions with experimental model scores.
- Disallows silent failure, fallback mock models, or runtime retraining.
- Strict PII quarantine: Does not log sensitive patient symptoms or send them to external services.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import joblib
import numpy as np

MODEL_BUNDLE_PATH = Path("models/disease_prediction/logisticregression_best.joblib")
METADATA_PATH = Path("models/disease_prediction/logisticregression_metadata.json")

CLINICAL_DISCLAIMER = (
    "This is an experimental machine-learning prediction based on a limited, "
    "highly duplicated-source dataset after deduplication. It is not a medical diagnosis. "
    "Consult a qualified healthcare professional for clinical assessment."
)

MIN_SYMPTOMS_FOR_INFERENCE = 3
EVIDENCE_CONFIDENCE_THRESHOLD = 0.25
EVIDENCE_MARGIN_THRESHOLD = 0.05

class PredictionStatus:
    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"

class DiseasePredictionService:
    def __init__(self, model_path: Path = MODEL_BUNDLE_PATH, metadata_path: Path = METADATA_PATH):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.pipeline = None
        self.feature_columns: List[str] = []
        self.feature_to_idx: Dict[str, int] = {}
        self.target_classes: np.ndarray = np.array([])
        self.model_name: str = ""
        self.version: str = "v1-deduplicated"
        self._load_and_validate()

    def _load_and_validate(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Disease prediction model bundle not found at: {self.model_path.resolve()}")
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Model metadata not found at: {self.metadata_path.resolve()}")

        with open(self.metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        bundle = joblib.load(self.model_path)
        if not isinstance(bundle, dict) or "pipeline" not in bundle:
            raise ValueError("Invalid model bundle format. Expected dict containing 'pipeline'.")

        self.pipeline = bundle["pipeline"]
        self.feature_columns = bundle.get("feature_names", metadata.get("feature_columns_in_order", []))
        self.target_classes = np.array(bundle.get("classes", metadata.get("target_classes", [])))
        self.model_name = bundle.get("model_name", metadata.get("model_name", "LogisticRegression"))

        # Strict integrity assertions
        if len(self.feature_columns) != 132:
            raise ValueError(f"Feature count mismatch! Expected 132 symptom features, found {len(self.feature_columns)}.")
        if len(self.target_classes) != 41:
            raise ValueError(f"Target classes count mismatch! Expected 41 classes, found {len(self.target_classes)}.")

        self.feature_to_idx = {name: idx for idx, name in enumerate(self.feature_columns)}

    def predict_top_k(self, symptoms: List[str], top_k: int = 3) -> Dict[str, Any]:
        """
        Converts symptom checklist into 132-binary feature vector and computes top-k differential rankings.
        """
        if not symptoms:
            raise ValueError("Symptom list cannot be empty.")

        # Check duplicates
        if len(symptoms) != len(set(symptoms)):
            raise ValueError("Duplicate symptom names detected in request.")

        # Validate each symptom against supported 132 feature names
        unknown = [s for s in symptoms if s not in self.feature_to_idx]
        if unknown:
            raise ValueError(f"Unknown symptom feature(s): {unknown}. Please reference official feature names.")

        # Build 132-binary vector in exact sequence
        vector = np.zeros((1, len(self.feature_columns)), dtype=int)
        for s in symptoms:
            vector[0, self.feature_to_idx[s]] = 1

        # Predict probabilities
        if hasattr(self.pipeline, "predict_proba"):
            proba_matrix = self.pipeline.predict_proba(vector)[0]
        else:
            # Fallback for decision function softmax
            dfunc = self.pipeline.decision_function(vector)[0]
            exp_d = np.exp(dfunc - np.max(dfunc))
            proba_matrix = exp_d / np.sum(exp_d)

        # Rank Top-K classes
        sorted_indices = np.argsort(proba_matrix)[::-1]
        top1_score = float(proba_matrix[sorted_indices[0]])
        top2_score = float(proba_matrix[sorted_indices[1]]) if len(sorted_indices) > 1 else 0.0
        score_margin = top1_score - top2_score

        # Abstention & Confidence Assessment
        # Case A: Fewer than 3 recognized symptoms -> INSUFFICIENT_INFORMATION (cannot distinguish 41 diseases)
        if len(symptoms) < MIN_SYMPTOMS_FOR_INFERENCE:
            evidence_status = PredictionStatus.INSUFFICIENT_INFORMATION
            abstention_reason = (
                f"Insufficient symptom information provided ({len(symptoms)} symptom(s) provided; minimum of {MIN_SYMPTOMS_FOR_INFERENCE} required). "
                "The statistical model cannot reliably differentiate between 41 diagnostic categories with isolated or very sparse symptoms."
            )
            # When abstaining due to insufficient information, do NOT display misleading top predictions as candidates
            display_predictions = []
        # Case B: Top score below validation threshold (0.25) or margin below 0.05 -> LOW_CONFIDENCE
        elif top1_score < EVIDENCE_CONFIDENCE_THRESHOLD or score_margin < EVIDENCE_MARGIN_THRESHOLD:
            evidence_status = PredictionStatus.LOW_CONFIDENCE
            abstention_reason = (
                f"Low-confidence statistical prediction (Top model score {round(top1_score, 4)} or separation margin {round(score_margin, 4)} "
                f"below empirical validation criteria of score >= {EVIDENCE_CONFIDENCE_THRESHOLD} and margin >= {EVIDENCE_MARGIN_THRESHOLD}). "
                "Multiple disease categories have overlapping, indistinguishable probabilities."
            )
            # Include top-k predictions with explicit low-confidence flag
            display_predictions = []
            for rank, idx in enumerate(sorted_indices[:top_k], 1):
                disease = str(self.target_classes[idx]).strip()
                score = float(proba_matrix[idx])
                display_predictions.append({
                    "rank": rank,
                    "disease_category": disease,
                    "experimental_model_score": round(score, 4)
                })
        # Case C: Meets validation empirical threshold
        else:
            evidence_status = PredictionStatus.SUFFICIENT_EVIDENCE
            abstention_reason = None
            display_predictions = []
            for rank, idx in enumerate(sorted_indices[:top_k], 1):
                disease = str(self.target_classes[idx]).strip()
                score = float(proba_matrix[idx])
                display_predictions.append({
                    "rank": rank,
                    "disease_category": disease,
                    "experimental_model_score": round(score, 4)
                })

        return {
            "predictions": display_predictions,
            "evidence_status": evidence_status,
            "abstention_reason": abstention_reason,
            "top_model_score": round(top1_score, 4) if len(symptoms) > 0 else 0.0,
            "score_margin": round(score_margin, 4) if len(symptoms) > 0 else 0.0,
            "symptoms_supplied_count": len(symptoms),
            "model_identifier": f"{self.model_name}:{self.version}",
            "disclaimer": CLINICAL_DISCLAIMER
        }

# Global cached singleton instance
_prediction_service: Optional[DiseasePredictionService] = None

def get_disease_prediction_service() -> DiseasePredictionService:
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = DiseasePredictionService()
    return _prediction_service

