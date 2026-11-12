"""
FastAPI Router for Evidence-Grounded Medical Reference Inquiries (Gemini RAG)
POST /api/v1/medical/ask
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from rag.medical_rag import MedicalRAGService

router = APIRouter(prefix="/medical", tags=["Medical Reference Knowledge"])

# Singleton instance of RAG service (lazy loaded)
_rag_service: Optional[MedicalRAGService] = None

def get_rag_service() -> MedicalRAGService:
    global _rag_service
    if _rag_service is None:
        from rag.retrieval import MedicalRetrievalService
        retriever = MedicalRetrievalService(namespace="medical-references-v2")
        _rag_service = MedicalRAGService(retrieval_service=retriever, similarity_threshold=0.38)
    return _rag_service

class AskMedicalRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="Clinical or medical inquiry text")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of evidence chunks to retrieve")
    topic_filter: Optional[str] = Field(default=None, description="Optional medical topic filter ('diabetes', 'hypertension', 'cardiovascular')")

class CitationItem(BaseModel):
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    title: Optional[str] = None
    source_organization: Optional[str] = None
    source_url: Optional[str] = None
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    verification_status: Optional[str] = None

class SafetyFlags(BaseModel):
    is_emergency: bool = False
    emergency_reasons: List[str] = []
    is_prompt_injection: bool = False
    requires_urgent_escalation: bool = False

class AskMedicalResponse(BaseModel):
    question: str
    answer: str
    evidence_status: str
    safety_flags: SafetyFlags
    citations: List[CitationItem] = []
    rejected_citations: List[Dict[str, Any]] = []
    emergency_directive: Optional[str] = None
    disclaimer: str
    model_id: str
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float

@router.post("/ask", response_model=AskMedicalResponse)
def ask_medical_reference(
    request: AskMedicalRequest,
    rag_service: MedicalRAGService = Depends(get_rag_service)
):
    """
    Submit a medical reference inquiry.
    Retrieves evidence from official clinical guidelines (MedlinePlus, WHO),
    synthesizes a grounded answer via Google Gemini API, and verifies citations.
    """
    try:
        result = rag_service.answer_medical_inquiry(
            question=request.question,
            top_k=request.top_k,
            topic_filter=request.topic_filter
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Medical RAG processing failed: {str(e)}"
        )

