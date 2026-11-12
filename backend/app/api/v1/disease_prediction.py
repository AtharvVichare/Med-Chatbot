"""
FastAPI Router for Symptom-Based Disease Prediction & Grounded Explanations
Endpoints:
- POST /api/v1/disease/predict: Generates top-3 ranked differential disease predictions.
- GET  /api/v1/disease/symptoms: Lists 132 supported symptom feature names.
- POST /api/v1/disease/explain: Grounds experimental ML predictions in official clinical reference guidelines using Gemini RAG.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, field_validator

from backend.app.services.disease_prediction import (
    DiseasePredictionService,
    get_disease_prediction_service,
    CLINICAL_DISCLAIMER,
    PredictionStatus
)
from backend.app.services.disease_explanation import (
    DiseaseExplanationService,
    get_disease_explanation_service,
    EXPLANATION_DISCLAIMER
)
from backend.app.services.safety_triage import (
    evaluate_safety_warnings,
    SafetyWarning,
    SafetyTriageLevel
)
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User

router = APIRouter(prefix="/disease", tags=["Disease Prediction (Experimental)"])

# --- Schemas for POST /predict ---
class SymptomPredictRequest(BaseModel):
    symptoms: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of symptom feature names observed (e.g. ['fatigue', 'vomiting', 'high_fever'])",
        examples=[["fatigue", "vomiting", "high_fever"]]
    )
    # Optional symptom-quality fields (kept distinct from 132-symptom feature vector)
    duration: Optional[str] = Field(None, description="Symptom duration (e.g. '< 24 hours', '1-3 days', '1-2 weeks', '> 2 weeks')")
    severity: Optional[str] = Field(None, description="Symptom severity ('mild', 'moderate', 'severe', 'critical')")
    progression: Optional[str] = Field(None, description="Progression trajectory ('improving', 'stable', 'worsening')")
    has_fever: Optional[bool] = Field(None, description="Explicit fever indicator")
    breathing_difficulty: Optional[bool] = Field(None, description="Explicit breathing difficulty / respiratory distress indicator")
    chest_discomfort: Optional[bool] = Field(None, description="Explicit chest discomfort / pain indicator")
    medical_history: Optional[List[str]] = Field(None, description="Relevant existing medical history flags")

    @field_validator("symptoms")
    def validate_symptoms_list(cls, v):
        if not v:
            raise ValueError("Symptom list cannot be empty.")
        cleaned = []
        for s in v:
            if not isinstance(s, str) or not s.strip():
                raise ValueError("Symptom names must be non-empty strings.")
            cleaned.append(s.strip())
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate symptom names detected in request.")
        return cleaned

class DiseasePredictionItem(BaseModel):
    rank: int = Field(..., description="Rank in differential list (1 to 3)")
    disease_category: str = Field(..., description="Predicted disease class name")
    experimental_model_score: float = Field(..., description="Experimental uncalibrated model output score (0.0 to 1.0)")

class SymptomPredictResponse(BaseModel):
    predictions: List[DiseasePredictionItem] = Field(default=[], description="Top-3 differential disease predictions (empty if model abstains)")
    evidence_status: str = Field(..., description="SUFFICIENT_EVIDENCE, LOW_CONFIDENCE, or INSUFFICIENT_INFORMATION")
    abstention_reason: Optional[str] = Field(None, description="Documented empirical rationale for abstention or low-confidence status")
    top_model_score: float = Field(default=0.0, description="Highest model score across all classes")
    score_margin: float = Field(default=0.0, description="Separation between top-1 and top-2 predictions")
    symptoms_supplied_count: int = Field(..., description="Number of recognized symptoms provided")
    safety_warnings: List[SafetyWarning] = Field(default=[], description="Independent clinical safety and triage advisories")
    model_identifier: str = Field(..., description="Model architecture and version")
    disclaimer: str = Field(..., description="Clinical safety and limitations disclaimer")

# --- Schemas for POST /explain ---
class DiseaseExplainRequest(BaseModel):
    predictions: List[DiseasePredictionItem] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="List of up to 3 predictions output by the ML disease classifier",
        examples=[[
            {"rank": 1, "disease_category": "Jaundice", "experimental_model_score": 0.2578},
            {"rank": 2, "disease_category": "Heart Attack", "experimental_model_score": 0.0642},
            {"rank": 3, "disease_category": "Bronchial Asthma", "experimental_model_score": 0.0573}
        ]]
    )
    model_identifier: Optional[str] = Field(
        default="LogisticRegression:v1-deduplicated",
        description="Identifier of model that produced the predictions"
    )

class CitationItem(BaseModel):
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    title: Optional[str] = None
    source_organization: Optional[str] = None
    source_url: Optional[str] = None
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    verification_status: Optional[str] = None

class DiseaseExplainResponse(BaseModel):
    original_predictions: List[DiseasePredictionItem] = Field(default=[], description="Original unchanged ML predictions")
    explanation: str = Field(..., description="Evidence-grounded educational explanation synthesized from reference guidelines")
    citations: List[CitationItem] = Field(default=[], description="Verified clinical reference citations")
    rejected_citations: List[Dict[str, Any]] = Field(default=[], description="Unverified citations rejected by validator")
    evidence_status: str = Field(..., description="Sufficiency status of medical reference evidence")
    safety_warnings: List[SafetyWarning] = Field(default=[], description="Independent clinical safety and triage advisories")
    disclaimer: str = Field(..., description="Non-diagnostic clinical advisory disclaimer")
    model_identifier: str = Field(..., description="Model identifier")
    retrieval_latency_ms: float = Field(..., description="Latency of Pinecone vector search in ms")
    generation_latency_ms: float = Field(..., description="Latency of Gemini API generation in ms")
    total_latency_ms: float = Field(..., description="Total end-to-end processing latency in ms")


# --- Endpoints ---
@router.get("/symptoms", response_model=List[str], summary="List supported symptom feature names")
def list_supported_symptoms(
    service: DiseasePredictionService = Depends(get_disease_prediction_service),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the complete list of 132 standardized symptom feature names recognized by the predictive model.
    """
    return service.feature_columns

@router.post(
    "/predict",
    response_model=SymptomPredictResponse,
    summary="Predict differential disease rankings from symptom checklist with safety triage",
    responses={
        200: {"description": "Top-3 differential predictions computed successfully."},
        400: {"description": "Invalid symptom input (e.g. unknown symptoms, duplicates, empty list)."},
        401: {"description": "Authentication failure (invalid or missing Bearer token)."},
        500: {"description": "Internal model failure or uninitialized artifact."}
    }
)
def predict_disease_from_symptoms(
    request: SymptomPredictRequest,
    service: DiseasePredictionService = Depends(get_disease_prediction_service),
    current_user: User = Depends(get_current_user)
):
    """
    Experimental Machine Learning Disease Prediction Endpoint with Safety Abstention.
    
    Accepts a list of recognized symptom feature names and optional clinical quality descriptors.
    Executes an independent deterministic safety triage layer, evaluates model evidence sufficiency,
    and returns either calibrated abstention guidance or ranked predictions.
    """
    try:
        # Step 1: Independent clinical safety warning layer (runs regardless of ML model)
        safety_warnings = evaluate_safety_warnings(
            symptoms=request.symptoms,
            duration=request.duration,
            severity=request.severity,
            progression=request.progression,
            has_fever=request.has_fever,
            breathing_difficulty=request.breathing_difficulty,
            chest_discomfort=request.chest_discomfort,
            medical_history=request.medical_history
        )

        # Step 2: Compute model predictions with abstention logic
        result = service.predict_top_k(symptoms=request.symptoms, top_k=3)
        result["safety_warnings"] = safety_warnings
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference processing failed: {str(e)}"
        )

@router.post(
    "/explain",
    response_model=DiseaseExplainResponse,
    summary="Grounded clinical explanation of ML disease predictions",
    responses={
        200: {"description": "Educational explanation generated successfully with verified citations."},
        400: {"description": "Invalid prediction metadata (unknown disease class, non-finite scores, out-of-order ranks)."},
        401: {"description": "Authentication failure (invalid or missing Bearer token)."},
        500: {"description": "Internal processing or synthesis error."}
    }
)
def explain_disease_predictions(
    request: DiseaseExplainRequest,
    service: DiseaseExplanationService = Depends(get_disease_explanation_service),
    current_user: User = Depends(get_current_user)
):
    """
    Grounded Gemini Explanation Endpoint for ML Disease Predictions.
    
    Accepts the top-3 predicted disease categories and experimental model scores output by the
    trained ML classifier, retrieves public medical guidelines (MedlinePlus, WHO), and synthesizes
    an educational, evidence-grounded explanation.
    
    **Privacy & Safety Guarantees:**
    - Raw 132-feature symptom vectors and patient EHR records are NEVER sent to Gemini or Pinecone.
    - Gemini cannot change, re-rank, or invent disease predictions.
    - All claims are cross-checked against retrieved references by CitationValidator.
    """
    try:
        dict_preds = [p.model_dump() for p in request.predictions]
        result = service.explain_predictions(
            predictions=dict_preds,
            model_identifier=request.model_identifier or "LogisticRegression:v1-deduplicated"
        )
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation processing failed: {str(e)}"
        )

@router.post(
    "/predict-and-explain",
    response_model=DiseaseExplainResponse,
    summary="Secure End-to-End Prediction and Grounded Explanation with Safety Layer",
    responses={
        200: {"description": "End-to-end classification and grounded explanation generated securely."},
        400: {"description": "Invalid symptom input (e.g. unknown symptoms, duplicates, empty list)."},
        401: {"description": "Authentication failure (invalid or missing Bearer token)."},
        500: {"description": "Internal model failure or synthesis error."}
    }
)
def predict_and_explain(
    request: SymptomPredictRequest,
    pred_service: DiseasePredictionService = Depends(get_disease_prediction_service),
    explain_service: DiseaseExplanationService = Depends(get_disease_explanation_service),
    current_user: User = Depends(get_current_user)
):
    """
    Secure Integrated Disease Prediction and Explanation Pipeline (Server-Enforced).
    
    Executes the independent safety warning triage, runs the trained ML model internally,
    evaluates abstention conditions, and only invokes external Gemini explanation when
    sufficient empirical model evidence exists.
    """
    try:
        # Step 1: Independent clinical safety warning layer
        safety_warnings = evaluate_safety_warnings(
            symptoms=request.symptoms,
            duration=request.duration,
            severity=request.severity,
            progression=request.progression,
            has_fever=request.has_fever,
            breathing_difficulty=request.breathing_difficulty,
            chest_discomfort=request.chest_discomfort,
            medical_history=request.medical_history
        )

        # Step 2: Run internal trained classifier with abstention evaluation
        pred_result = pred_service.predict_top_k(symptoms=request.symptoms, top_k=3)
        predictions = pred_result["predictions"]
        model_id = pred_result.get("model_identifier", "LogisticRegression:v1-deduplicated")
        evidence_status = pred_result.get("evidence_status", PredictionStatus.SUFFICIENT_EVIDENCE)
        abstention_reason = pred_result.get("abstention_reason")

        # Step 3: Handle Abstention States without invoking external LLM
        if evidence_status == PredictionStatus.INSUFFICIENT_INFORMATION or not predictions:
            return DiseaseExplainResponse(
                original_predictions=[],
                explanation=(
                    f"Model Abstention Notice: {abstention_reason}\n\n"
                    "Because there is insufficient symptom evidence to differentiate between medical conditions, "
                    "no external generative explanation was produced. Please consult a qualified physician for a clinical evaluation."
                ),
                citations=[],
                rejected_citations=[],
                evidence_status="INSUFFICIENT_EVIDENCE",
                safety_warnings=safety_warnings,
                disclaimer=CLINICAL_DISCLAIMER,
                model_identifier=model_id,
                retrieval_latency_ms=0.0,
                generation_latency_ms=0.0,
                total_latency_ms=0.0
            )

        # Step 4: When predictions exist, generate grounded reference explanation
        explain_result = explain_service.explain_predictions(
            predictions=predictions,
            model_identifier=model_id
        )
        explain_result["safety_warnings"] = safety_warnings
        if evidence_status == PredictionStatus.LOW_CONFIDENCE and abstention_reason:
            explain_result["explanation"] = f"Caution - Low Confidence Statistical Predictions:\n{abstention_reason}\n\n" + explain_result.get("explanation", "")

        return explain_result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Predict-and-explain processing failed: {str(e)}"
        )
