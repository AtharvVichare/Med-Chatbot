"""
Longitudinal Future Disease Risk Forecasting API Router
Provides comprehensive, evidence-based prospective disease risk predictions
across multiple chronic disease domains based on genuine patient EHR observations.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.db.models import Patient
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User
from backend.app.services.clinical_future_risk_service import (
    ClinicalFutureRiskService,
    ComprehensiveFutureRiskResponse,
    RESEARCH_DISCLAIMER
)

router = APIRouter(prefix="/insights", tags=["Future Health Insights"])


# Legacy Backward-Compatible Schema
class LegacyFutureRiskResponse(BaseModel):
    patient_id: str
    target_condition: str = "Incident Type 2 Diabetes Mellitus"
    prediction_horizon: str = "12 Months"
    lookback_window: str = "24 Months"
    status: str  # 'EVALUATED', 'PRE_EXISTING_CONDITION', 'INSUFFICIENT_HISTORICAL_DATA'
    estimated_risk_score: Optional[float] = None
    risk_category: Optional[str] = None  # Low, Moderate, Elevated, Diagnosed, Indeterminate
    contributing_factors: List[Dict[str, Any]] = []
    historical_metrics_analyzed: Dict[str, Any] = {}
    clinical_disclaimer: str = RESEARCH_DISCLAIMER


@router.get("/future-risk/{patient_id}", response_model=ComprehensiveFutureRiskResponse)
def get_comprehensive_future_disease_risk(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Comprehensive Multi-System Future Disease Risk Prediction.
    Evaluates cardiovascular, vascular, metabolic, renal, and pulmonary domains
    without defaulting to diabetes or fabricating missing biomarker records.
    """
    # Enforce patient-level authorization
    if current_user.role == "patient" and current_user.patient_id != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Unauthorized access to patient risk profile."
        )

    patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id))
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Patient record '{patient_id}' not found."
        )

    try:
        response = ClinicalFutureRiskService.evaluate_patient_future_risk(db, patient_id)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute clinical risk evaluation: {str(e)}"
        )


@router.get("/diabetes-risk/{patient_id}", response_model=LegacyFutureRiskResponse)
def evaluate_12mo_diabetes_risk(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Legacy-compatible endpoint for 12-month diabetes evaluation.
    Powered by the genuine ClinicalFutureRiskService.
    If the patient lacks glycemic data, transparently reports INSUFFICIENT_HISTORICAL_DATA
    rather than guessing.
    """
    if current_user.role == "patient" and current_user.patient_id != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Unauthorized access to patient risk profile."
        )

    patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id))
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Patient record not found."
        )

    full_evaluation = ClinicalFutureRiskService.evaluate_patient_future_risk(db, patient_id)

    # Locate the specific Type 2 Diabetes evaluation
    dm_eval = next(
        (e for e in full_evaluation.condition_evaluations if e.icd10_code == "E11.9"),
        None
    )

    if not dm_eval or dm_eval.status == "INSUFFICIENT_BIOMARKERS":
        return LegacyFutureRiskResponse(
            patient_id=patient_id,
            target_condition="Incident Type 2 Diabetes Mellitus",
            prediction_horizon="12 Months",
            lookback_window="24 Months",
            status="INSUFFICIENT_HISTORICAL_DATA",
            estimated_risk_score=None,
            risk_category="Indeterminate",
            contributing_factors=[
                {
                    "factor": "Missing Baseline Glycemic Labs",
                    "detail": "No historical fasting blood glucose or HbA1c observations recorded in EHR."
                }
            ],
            historical_metrics_analyzed=full_evaluation.historical_metrics_analyzed,
            clinical_disclaimer=RESEARCH_DISCLAIMER
        )

    if dm_eval.status == "PRE_EXISTING_CONDITION":
        return LegacyFutureRiskResponse(
            patient_id=patient_id,
            target_condition="Incident Type 2 Diabetes Mellitus",
            prediction_horizon="12 Months",
            lookback_window="24 Months",
            status="PRE_EXISTING_CONDITION",
            estimated_risk_score=1.0,
            risk_category="Diagnosed",
            contributing_factors=[
                {"factor": f.factor, "detail": f.detail or f.metric or ""}
                for f in dm_eval.contributing_factors
            ],
            historical_metrics_analyzed=full_evaluation.historical_metrics_analyzed,
            clinical_disclaimer=RESEARCH_DISCLAIMER
        )

    return LegacyFutureRiskResponse(
        patient_id=patient_id,
        target_condition="Incident Type 2 Diabetes Mellitus",
        prediction_horizon="12 Months",
        lookback_window="24 Months",
        status="EVALUATED",
        estimated_risk_score=dm_eval.risk_score,
        risk_category=dm_eval.risk_tier,
        contributing_factors=[
            {"factor": f.factor, "metric": f.metric, "impact": f.impact, "detail": f.detail}
            for f in dm_eval.contributing_factors
        ],
        historical_metrics_analyzed=full_evaluation.historical_metrics_analyzed,
        clinical_disclaimer=RESEARCH_DISCLAIMER
    )
