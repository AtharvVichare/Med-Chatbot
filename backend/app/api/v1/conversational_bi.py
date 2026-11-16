"""
Conversational BI Router for Hospital Management
Translates natural-language operational & clinical questions into safe database analytics.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User
from backend.app.services.agents.conversational_bi_agent import ConversationalBIAgent

router = APIRouter(prefix="/conversational-bi", tags=["Conversational BI"])

class BIQueryRequest(BaseModel):
    query: str

@router.post("/query")
def run_bi_query(
    req: BIQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Executes a natural-language BI analytics query."""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty")

    try:
        return ConversationalBIAgent.query(req.query.strip(), db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"BI Query execution failed: {str(e)}")
