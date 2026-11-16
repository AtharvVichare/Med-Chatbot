"""
Multi-Agent Orchestration & Event Bus Router
Provides:
- Live feed of inter-agent events and communications
- Human escalation resolution (clinical, administrative, financial)
- Direct agent task delegation
- Drug interaction safety checks
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User
from backend.app.services.agent_event_bus import AgentEventBus
from backend.app.services.agents.intake_agent import IntakeAgent
from backend.app.services.agents.lab_pharmacy_agent import LabPharmacyAgent
from backend.app.services.agents.procurement_agent import ProcurementAgent

router = APIRouter(prefix="/agents", tags=["Multi-Agent AI Architecture"])

class ResolveEscalationRequest(BaseModel):
    action: str  # "approve" or "reject"
    resolution_notes: str

class TriageIntakeRequest(BaseModel):
    message: str
    patient_id: Optional[str] = None

class DrugSafetyCheckRequest(BaseModel):
    patient_id: str
    proposed_medication: str

@router.get("/events")
def list_agent_events(
    limit: int = 40,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves live multi-agent communication and task feed."""
    return AgentEventBus.get_recent_events(limit=limit, db=db)

@router.post("/escalations/{event_id}/resolve")
def resolve_escalation(
    event_id: str,
    req: ResolveEscalationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolves an inter-agent task escalated for human clinical or management approval."""
    try:
        return AgentEventBus.resolve_escalation(
            event_id=event_id,
            action=req.action,
            resolution_notes=req.resolution_notes,
            user_id=current_user.full_name or current_user.username,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/triage-intake")
def triage_intake_message(
    req: TriageIntakeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Runs the Intake Agent on patient symptoms to recommend doctors or admissions."""
    target_pid = req.patient_id or current_user.patient_id or "PAT-00001"
    try:
        return IntakeAgent.process_patient_request(req.message, target_pid, db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/safety-check")
def check_medication_safety(
    req: DrugSafetyCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Runs the Lab/Pharmacy Agent to verify drug-drug interactions and allergies."""
    try:
        return LabPharmacyAgent.check_drug_safety(req.proposed_medication, req.patient_id, db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
