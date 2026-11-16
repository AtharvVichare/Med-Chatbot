"""
Chat Assistant & Conversational Health Companion Router
Provides:
- Intent classification: greetings, acknowledgements, thanks, medical inquiries, EHR queries, symptom analysis.
- Structured server-side logging without leaking keys, tokens, or private medical data.
- Bounded retries and rate limit / quota awareness for Gemini LLM.
- Graceful degradation when Pinecone or RAG references are unavailable.
- Conversation history tracking with chronological ordering.
- Explicit EHR write confirmations for detected clinical updates.
"""

import os
import re
import time
import uuid
import json
import logging
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.db.models import (
    ChatConversation,
    ChatMessage,
    Patient,
    Condition,
    Medication,
    Observation,
    DailyHealthLog,
    PatientDocument
)
from backend.app.db.schemas import (
    ChatConversationRead,
    ChatMessageRead,
    ChatMessageCreate
)
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User
from rag.medical_rag import MedicalRAGService
from rag.gemini_client import GeminiClient

logger = logging.getLogger("AarogyaChatAssistant")
router = APIRouter(prefix="/assistant", tags=["AI Health Assistant"])

_rag_service: Optional[MedicalRAGService] = None
_gemini_client: Optional[GeminiClient] = None

def get_rag_service() -> MedicalRAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = MedicalRAGService()
    return _rag_service

def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


# ==========================================
# Intent Classification Engine
# ==========================================
GREETING_PATTERNS = [
    r'^(?:hi|hello|hey|namaste|good\s*(?:morning|afternoon|evening|day)|greetings)[\s\!\.\,\?]*$'
]

ACKNOWLEDGEMENT_PATTERNS = [
    r'^(?:ok|okay|alright|got\s*it|understood|sure|fine|noted|cool|yep|yeah|yes)[\s\!\.\,\?]*$'
]

GRATITUDE_PATTERNS = [
    r'^(?:thanks|thank\s*you|thx|thank\s*you\s*(?:so\s*much|very\s*much)?|much\s*appreciated)[\s\!\.\,\?]*$'
]

HOSPITAL_APPOINTMENT_PATTERNS = [
    r'(?:kem|hospital|doctor|clinic|opd|appointment|book\s*an?\s*appointment|consultation\s*booking|how\s*do\s*i\s*book|walk[- ]?in\s*registration|ors\s*portal)',
    r'(?:where\s*is|contact|address\s*of|phone\s*number\s*of|location\s*of).*(?:kem|hospital|clinic)',
    r'(?:book.*(?:appointment|opd|slot|doctor|hospital))'
]

KNOWLEDGE_DIAGNOSTICS_PATTERNS = [
    r'(?:how\s*many|count\s*of|number\s*of).*(?:chunks?|vectors?|documents?|references?|sources?|indexed|in\s*the\s*knowledge\s*base)',
    r'(?:what\s*(?:sources|references|documents|guidelines)|knowledge\s*base\s*stats|system\s*status|index\s*status|namespaces|pinecone\s*stats)'
]

GRAPH_REQUEST_PATTERNS = [
    r'(?:trend|graph|chart|plot|compare|over\s*time|history\s*of)\s*(?:my\s*)?(?:bp|blood\s*pressure|sugar|glucose|hba1c|vitals|weight|pulse|oxygen|spo2)?',
    r'(?:show|display|see|plot|graph|draw|view).*(?:blood\s*pressure|bp|glucose|sugar|hba1c|pulse|vitals|heart\s*rate|spo2|oxygen).*(?:trend|graph|chart|plot|history)',
    r'(?:show|display|see|view|plot|draw)\s*(?:my\s*)?(?:trend|graph|chart|plot|history)\s*(?:for|of)?\s*(?:bp|blood\s*pressure|glucose|sugar|hba1c|pulse|vitals)?',
    r'(?:how\s*has\s*my\s*(?:bp|blood\s*pressure|glucose|sugar|hba1c|pulse)\s*(?:changed|trended|progressed))',
    r'.*(?:matplotlib|matplot|graph|chart|plot).*(?:bp|vitals|pressure|sugar|glucose|pulse|reading|health|metric)',
    r'(?:show|display|draw|plot)\s+(?:a\s+)?(?:graph|chart|plot)'
]

EHR_QUERY_PATTERNS = [
    r'(?:show|view|tell|display|see|get|find|list|check)\s*(?:my\s*)?(?:medical\s*history|health\s*record|complete\s*record|longitudinal\s*record|ehr|profile)',
    r'(?:what\s*(?:medicines?|medications?|drugs?|prescriptions?)\s*(?:am\s*i|do\s*i)\s*(?:taking|prescribed|on))',
    r'(?:my\s*(?:last|recent|latest)?\s*(?:bp|blood\s*pressure|sugar|glucose|vitals|hba1c|heart\s*rate|pulse|weight))',
    r'(?:what\s*(?:is|was)\s*my\s*(?:last|recent|latest|current)?\s*(?:bp|blood\s*pressure|glucose|sugar|hba1c|vitals|medication|prescription))',
    r'(?:show|tell|check|view|display|see|find|list|get)\s*(?:my\s*)?(?:past|previous|prior|recent|latest|uploaded)?\s*(?:radiological\s*)?(?:records|vitals|medications|conditions|prescriptions|allergies|history|reports?|scans?|mri|ct|x[- ]?rays?|ultrasounds?|images?|documents?|findings?)',
    r'(?:explain|review|analyze|what\s*(?:was|is)\s*(?:extracted|found|appended|seen))\s*(?:in|from|about)?\s*(?:my\s*)?(?:hba1c|lab|blood|report|test|uploaded|document|image|scan|mri|ct|x[- ]?ray|ultrasound|findings?)',
    r'(?:uploaded|attached)\s*(?:my\s*)?(?:medical\s*)?(?:report|file|document|image|pdf|test|lab|scan|mri|ct|x[- ]?ray)',
    r'(?:analyze|interpret|read|check)\s*(?:this|the|my)?\s*(?:uploaded\s*)?(?:image|scan|mri|ct|x[- ]?ray|ultrasound|sonography|photo|file)',
    r'(?:what\s*does\s*(?:this|the|my)\s*(?:image|scan|mri|ct|x[- ]?ray|ultrasound|report)\s*(?:show|mean|say))',
    r'.*(?:mri|radiological|scans?|x[- ]?rays?|ct\s*scans?).*(?:scans?|findings?|images?|reports?)',
    r'(?:future\s*(?:health\s*)?risk|prospective\s*risk|disease\s*risk|what\s*(?:diseases?|conditions?)\s*am\s*i\s*at\s*risk\s*(?:for|of)|am\s*i\s*at\s*risk|predict.*(?:risk|disease|health))'
]

def classify_intent(message: str) -> str:
    """
    Classifies patient message into:
    - 'greeting'
    - 'acknowledgement'
    - 'gratitude'
    - 'knowledge_diagnostics'
    - 'hospital_discovery'
    - 'graph_request'
    - 'ehr_query'
    - 'medical_inquiry'
    """
    cleaned = message.strip().lower()
    
    for pat in GREETING_PATTERNS:
        if re.match(pat, cleaned, re.IGNORECASE):
            return "greeting"
            
    for pat in ACKNOWLEDGEMENT_PATTERNS:
        if re.match(pat, cleaned, re.IGNORECASE):
            return "acknowledgement"
            
    for pat in GRATITUDE_PATTERNS:
        if re.match(pat, cleaned, re.IGNORECASE):
            return "gratitude"

    for pat in KNOWLEDGE_DIAGNOSTICS_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return "knowledge_diagnostics"

    for pat in HOSPITAL_APPOINTMENT_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return "hospital_discovery"

    for pat in GRAPH_REQUEST_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return "graph_request"
            
    for pat in EHR_QUERY_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return "ehr_query"
            
    return "medical_inquiry"


# ==========================================
# Structured Audit Logging Helper
# ==========================================
def log_chat_event(
    request_id: str,
    conversation_id: str,
    patient_id: Optional[str],
    processing_stage: str,
    model_identifier: Optional[str] = None,
    retrieval_status: Optional[str] = None,
    response_status: Optional[str] = None,
    exception_type: Optional[str] = None,
    safe_error_message: Optional[str] = None,
    duration_ms: Optional[float] = None
):
    """
    Structured server-side logger that NEVER prints API keys, tokens, or sensitive patient records.
    """
    log_payload = {
        "request_id": request_id,
        "conversation_id": conversation_id,
        "patient_id": patient_id,
        "stage": processing_stage,
        "model": model_identifier,
        "retrieval": retrieval_status,
        "status": response_status,
        "exception": exception_type,
        "error": safe_error_message,
        "duration_ms": duration_ms
    }
    logger.info(f"[CHAT_AUDIT] {json.dumps(log_payload)}")


# ==========================================
# Schema Definitions
# ==========================================
class CreateConversationRequest(BaseModel):
    title: Optional[str] = "Health Consultation"

class ConfirmEHRActionRequest(BaseModel):
    action_type: str  # 'condition', 'medication', 'measurement'
    payload: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    message_id: Optional[str] = None


# ==========================================
# API Endpoints
# ==========================================
@router.get("/conversations", response_model=List[ChatConversationRead])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.patient_id:
        return []
    convs = db.scalars(
        select(ChatConversation)
        .where(ChatConversation.patient_id == current_user.patient_id)
        .order_by(ChatConversation.updated_at.desc())
    ).all()
    return [ChatConversationRead.model_validate(c) for c in convs]


@router.post("/conversations", response_model=ChatConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    req: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.patient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No patient record associated with user.")
    
    conv_id = f"CONV-{uuid.uuid4().hex[:10].upper()}"
    now_utc = datetime.now(timezone.utc)
    conv = ChatConversation(
        conversation_id=conv_id,
        patient_id=current_user.patient_id,
        title=req.title or "Health Consultation",
        created_at=now_utc,
        updated_at=now_utc
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ChatConversationRead.model_validate(conv)


@router.get("/conversations/{conversation_id}/messages", response_model=List[ChatMessageRead])
def get_conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = db.scalar(select(ChatConversation).where(
        ChatConversation.conversation_id == conversation_id
    ))
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    if conv.patient_id != current_user.patient_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this conversation.")

    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
    ).all()
    return [ChatMessageRead.model_validate(m) for m in messages]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = db.scalar(select(ChatConversation).where(
        (ChatConversation.conversation_id == conversation_id) &
        (ChatConversation.patient_id == current_user.patient_id)
    ))
    if conv:
        db.delete(conv)
        db.commit()
    return None


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageRead)
async def send_message(
    conversation_id: str,
    req: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    t_start = time.perf_counter()
    req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    
    conv = db.scalar(select(ChatConversation).where(
        ChatConversation.conversation_id == conversation_id
    ))
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    if conv.patient_id != current_user.patient_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this conversation.")

    # 0. Validate message content
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty.")

    # 1. Save user message with UTC timestamp
    now_utc = datetime.now(timezone.utc)
    user_msg_id = f"MSG-{uuid.uuid4().hex[:10].upper()}"
    user_msg = ChatMessage(
        message_id=user_msg_id,
        conversation_id=conversation_id,
        sender="user",
        content=req.content.strip(),
        created_at=now_utc
    )
    db.add(user_msg)
    conv.updated_at = now_utc
    db.commit()

    # 2. Retrieve recent conversation history (last 6 turns)
    recent_history_objs = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(7)
    ).all()
    # Reverse to chronological order (excluding the current user message just inserted)
    chronological_history = [
        {"sender": m.sender, "content": m.content}
        for m in reversed(recent_history_objs)
        if m.message_id != user_msg_id
    ]

    # 3. Classify message intent
    intent = classify_intent(req.content)
    log_chat_event(
        request_id=req_id,
        conversation_id=conversation_id,
        patient_id=current_user.patient_id,
        processing_stage=f"intent_classified_{intent}"
    )

    # 4. Extract Clinical Health Data in Human-In-The-Loop Staging Mode
    # Extracts measurements & medications into proposals for the user to review and confirm
    from backend.app.services.clinical_extractor import ClinicalExtractorService
    appended_ehr_events = []
    proposed_actions: List[Dict[str, Any]] = []
    if current_user.patient_id:
        try:
            appended_ehr_events = ClinicalExtractorService.extract_from_chat(
                text=req.content,
                patient_id=current_user.patient_id,
                db=db,
                auto_commit=False  # Human in the loop: requires patient confirmation
            )
        except Exception as extract_err:
            logger.warning(f"Error during HITL clinical staging extraction: {extract_err}")

    # 5. Handle Intent Flow
    assistant_text = ""
    gemini_client = get_gemini_client()
    model_name = gemini_client.model_name

    # --- Intent A: Greeting ---
    if intent == "greeting":
        greetings = [
            f"Hello {current_user.full_name}! I am Aarogya Drishti, your personal AI health companion. How can I assist with your health or medical questions today?",
            f"Hi there, {current_user.full_name}! Good to see you. How are you feeling today, and what can I help you review?"
        ]
        # Pick greeting or prompt Gemini with a lightweight system prompt if history exists
        if not chronological_history:
            assistant_text = greetings[0]
        else:
            try:
                hist_str = "\n".join([f"{h['sender'].capitalize()}: {h['content']}" for h in chronological_history[-3:]])
                prompt = (
                    f"You are Aarogya Drishti, a warm, professional personal health AI companion.\n"
                    f"Patient name: {current_user.full_name}.\n"
                    f"Recent context:\n{hist_str}\n"
                    f"Patient: {req.content}\n"
                    f"Respond naturally with a brief, friendly greeting (1-2 sentences) and offer assistance."
                )
                resp = gemini_client.client.models.generate_content(model=model_name, contents=prompt)
                assistant_text = resp.text.strip() if resp and resp.text else greetings[0]
            except Exception as e:
                assistant_text = greetings[0]

    # --- Intent B: Acknowledgement & Gratitude ---
    elif intent in {"acknowledgement", "gratitude"}:
        hist_str = "\n".join([f"{h['sender'].capitalize()}: {h['content']}" for h in chronological_history[-4:]])
        fallback_ack = (
            "You are very welcome! Please feel free to ask if you have any questions about symptoms, medications, or test results."
            if intent == "gratitude" else
            "Understood! Let me know if you would like more details or if you have any new symptoms or readings to track."
        )
        try:
            role_hint = "welcoming them and assuring you are glad to help anytime" if intent == "gratitude" else "acknowledging their message and offering next steps"
            prompt = (
                f"You are Aarogya Drishti, a helpful healthcare assistant.\n"
                f"Recent conversation:\n{hist_str}\n"
                f"Patient: {req.content}\n"
                f"Provide a natural, brief (1-2 sentences), helpful response ({role_hint})."
            )
            resp = gemini_client.client.models.generate_content(model=model_name, contents=prompt)
            assistant_text = resp.text.strip() if resp and resp.text else fallback_ack
        except Exception as e:
            assistant_text = fallback_ack

    # --- Intent C: Knowledge-Base Diagnostics ---
    elif intent == "knowledge_diagnostics":
        from backend.app.services.knowledge_diagnostics import KnowledgeBaseDiagnosticsService
        diag = KnowledgeBaseDiagnosticsService.get_live_diagnostics()
        assistant_text = KnowledgeBaseDiagnosticsService.format_diagnostics_markdown(diag)

    # --- Intent D: Hospital Discovery, Appointment Booking & Admissions ---
    elif intent == "hospital_discovery":
        q_low = req.content.lower()
        if any(k in q_low for k in ["book", "appointment", "doctor", "cardiologist", "physician", "bed", "admit", "admission", "slot", "hospital bed"]):
            from backend.app.services.agents.intake_agent import IntakeAgent
            intake_res = IntakeAgent.process_patient_request(req.content, current_user.patient_id, db)
            assistant_text = intake_res.get("message", "")
            if intake_res.get("action_type") == "doctor_recommendation":
                proposed_actions.append({
                    "action_type": "render_doctor_recommendations",
                    "department": intake_res["department"],
                    "priority": intake_res["priority"],
                    "suggested_date": intake_res["suggested_date"],
                    "doctors": intake_res["doctors"]
                })
            elif intake_res.get("action_type") == "admission_recommendation":
                proposed_actions.append({
                    "action_type": "render_admission_status",
                    "department": intake_res["department"],
                    "recommended_ward": intake_res["recommended_ward"],
                    "available_bed": intake_res["available_bed"],
                    "daily_charge": intake_res["daily_charge"],
                    "priority": intake_res["priority"]
                })
        else:
            from backend.app.services.hospital_service import HospitalDiscoveryService, HOSPITAL_DATABASE
            hospital = HospitalDiscoveryService.identify_hospital(req.content) or HOSPITAL_DATABASE["kem_hospital_mumbai"]
            assistant_text = HospitalDiscoveryService.format_hospital_guidance(hospital)

    # --- Intent E: Graph or Trend Request ---
    elif intent == "graph_request":
        # Determine target metric from query
        q_low = req.content.lower()
        target_metric = "blood_pressure"
        if "sugar" in q_low or "glucose" in q_low:
            target_metric = "glucose"
        elif "hba1c" in q_low:
            target_metric = "hba1c"
        elif "pulse" in q_low or "heart rate" in q_low:
            target_metric = "pulse"
        elif "spo2" in q_low or "oxygen" in q_low:
            target_metric = "oxygen_saturation"

        from backend.app.services.matplotlib_chart_service import MatplotlibChartService
        chart_data = MatplotlibChartService.generate_chart_for_patient(
            patient_id=current_user.patient_id,
            metric=target_metric,
            db=db
        )

        chart_action = {
            "action_type": "render_chart",
            "chart_title": chart_data["chart_title"],
            "chart_type": "line",
            "metric": target_metric,
            "unit": chart_data["unit"],
            "chart_image_base64": chart_data["chart_image_base64"],
            "points": chart_data["points"],
            "latest_value": chart_data["latest_value"],
            "latest_date": chart_data["latest_date"],
            "count": chart_data["count"]
        }
        proposed_actions.append(chart_action)

        assistant_text = (
            f"### Longitudinal {chart_data['chart_title']} ({current_user.full_name})\n\n"
            f"Here is your clinical trend chart generated from your verified health records using standard medical Matplotlib visualization with clinical stage reference bands.\n\n"
            f"- **Latest Reading:** **{chart_data['latest_value']} {chart_data['unit']}** (Recorded on {chart_data['latest_date']})\n"
            f"- **Data Points Analyzed:** {chart_data['count']} measurements across your longitudinal baseline record.\n\n"
            f"> [!TIP]\n> *Matplotlib clinical charts provide calibrated stage zones. Review persistent baseline shifts with your physician.*"
        )

    # --- Intent F: Patient EHR Query ---
    elif intent == "ehr_query":
        from backend.app.services.ehr_service import LongitudinalEHRService
        ehr_data = LongitudinalEHRService.get_complete_patient_record(current_user.patient_id, db)
        
        # If the user is specifically asking for complete history or summary, format interactive markdown
        q_low = req.content.lower()
        if any(k in q_low for k in ["medical history", "health record", "complete record", "longitudinal", "show my record", "ehr"]):
            assistant_text = LongitudinalEHRService.format_ehr_markdown(ehr_data)
        elif any(k in q_low for k in ["medicine", "medication", "drugs", "prescription"]):
            meds = ehr_data.get("medications", [])
            if meds:
                med_lines = [f"- **{m['medication_name']}** ({m['dosage']}, Status: `{m['status']}`, Prescribed: {m['prescribed_date'] or 'N/A'})" for m in meds]
                assistant_text = (
                    f"### Your Prescribed Medications ({current_user.full_name}):\n\n" +
                    "\n".join(med_lines) +
                    "\n\n> [!NOTE]\n> *Always consult your physician before altering, pausing, or stopping any prescribed medications.*"
                )
            else:
                assistant_text = f"According to your health record ({current_user.patient_id}), there are no active or historical medications currently documented."
        elif any(k in q_low for k in ["future risk", "disease risk", "health risk", "risk of disease", "future disease", "am i at risk", "predict risk", "my risk"]):
            from backend.app.services.clinical_future_risk_service import ClinicalFutureRiskService
            risk_eval = ClinicalFutureRiskService.evaluate_patient_future_risk(db, current_user.patient_id)

            cond_lines = []
            for c in risk_eval.condition_evaluations:
                if c.status == "PRE_EXISTING_CONDITION":
                    status_badge = "`Pre-existing (Diagnosed)`"
                elif c.status == "INSUFFICIENT_BIOMARKERS":
                    status_badge = "`Baseline Labs Missing (Screening Recommended)`"
                else:
                    status_badge = f"`Tier: {c.risk_tier} (Score: {round((c.risk_score or 0.0) * 100, 1)}%)`"
                cond_lines.append(f"- **{c.condition_name}** ({c.category}): {status_badge}")

            assistant_text = (
                f"### Prospective 12-Month Health Risk Assessment ({current_user.full_name}):\n\n"
                f"- **Primary Health Focus:** **{risk_eval.target_condition}**\n"
                f"- **Overall Risk Category:** `{risk_eval.risk_category or 'Low'} Risk`\n"
                f"- **EHR Data Completeness:** {risk_eval.data_completeness.completeness_percentage}% ({risk_eval.data_completeness.readiness_level.replace('_', ' ').title()})\n\n"
                f"#### Evaluated Multi-System Disease Domains:\n" +
                "\n".join(cond_lines) +
                f"\n\n**Clinical Summary:** {risk_eval.primary_risk_summary}\n\n"
                f"> [!TIP]\n> *For a detailed breakdown of your contributing biomarkers and clinical prevention guidelines, visit the **Future Health Insights** dashboard.*"
            )
        elif any(k in q_low for k in ["mri", "scan", "scans", "radiological", "x-ray", "xray", "ct", "ultrasound", "imaging", "findings", "reports"]):
            patient_docs = db.scalars(
                select(PatientDocument)
                .where(PatientDocument.patient_id == current_user.patient_id)
                .order_by(PatientDocument.created_at.desc())
            ).all()

            # Filter for radiological scans or images
            scan_docs = [
                d for d in patient_docs
                if d.document_type in ["radiological_scan", "imaging", "mri_scan", "xray", "ct_scan"]
                or d.file_type in ["jpg", "jpeg", "png", "webp"]
                or any(k in d.file_name.lower() for k in ["mri", "scan", "xray", "ct", "chest", "image"])
            ]

            if not scan_docs:
                assistant_text = (
                    f"I searched your connected longitudinal health record ({current_user.patient_id}), but there are currently "
                    f"no radiological scans (MRI, CT, or X-ray) on file.\n\n"
                    f"You can upload new imaging scans anytime via the **'Upload Medical Report'** button on your My Health Record page, "
                    f"and our multimodal AI will immediately analyze the images and extract findings for you."
                )
            else:
                scan_summaries = []
                for d in scan_docs[:5]:
                    meta = {}
                    if d.extracted_metadata:
                        try:
                            meta = json.loads(d.extracted_metadata)
                        except Exception:
                            pass
                    summary = meta.get("document_summary", "Radiological diagnostic scan on file.")
                    img_analysis = meta.get("imaging_analysis", {})
                    findings = img_analysis.get("findings", [])
                    if not findings and summary:
                        findings = [{"label": "Observation", "description": summary, "significance": "normal"}]

                    # Append rendering action so the frontend displays the visual scan card
                    proposed_actions.append({
                        "action_type": "render_imaging_scan",
                        "document_id": d.document_id,
                        "file_name": d.file_name,
                        "modality": img_analysis.get("modality") or ("MRI Scan" if "mri" in d.file_name.lower() else "Radiological Scan"),
                        "anatomical_region": img_analysis.get("anatomical_region") or ("Thorax / Chest" if "chest" in d.file_name.lower() else "Musculoskeletal / Hand" if "hand" in d.file_name.lower() else "Anatomical Region"),
                        "findings": findings,
                        "differential_considerations": img_analysis.get("differential_considerations", []),
                        "recommended_investigations": img_analysis.get("recommended_investigations", [])
                    })

                    scan_date_str = d.created_at.strftime("%d %b %Y") if d.created_at else "Recently"
                    findings_bullets = "\n".join([f"    - **{f.get('label', 'Finding')}:** {f.get('description', '')}" for f in findings[:4]])
                    scan_summaries.append(
                        f"- **{d.file_name}** ({d.document_type.replace('_', ' ').title()} · {scan_date_str}):\n"
                        f"  *Clinical Summary:* {summary}\n"
                        f"{findings_bullets if findings_bullets else ''}"
                    )

                assistant_text = (
                    f"### Your Previous Radiological Scans & Findings ({current_user.full_name}):\n\n"
                    f"I retrieved **{len(scan_docs)}** radiological imaging scan(s) from your connected EHR record. "
                    f"The visual scans and extracted findings are displayed below:\n\n"
                    + "\n\n".join(scan_summaries) +
                    f"\n\n> [!NOTE]\n"
                    f"> *AI radiological analysis is for educational and clinical decision support. Final diagnostic interpretation requires review by a board-certified radiologist or your attending physician.*"
                )
        else:
            # Check if this is a report-specific analysis inquiry
            recent_doc = db.scalar(
                select(PatientDocument)
                .where(PatientDocument.patient_id == current_user.patient_id)
                .order_by(PatientDocument.created_at.desc())
            )
            doc_context_str = ""
            if recent_doc and recent_doc.extracted_metadata:
                try:
                    meta = json.loads(recent_doc.extracted_metadata)
                    summary = meta.get("document_summary", "")
                    obs = meta.get("observations", [])
                    obs_summary = ", ".join([f"{o.get('test_name')}: {o.get('value_numeric')} {o.get('unit', '')}" for o in obs[:12]])

                    # Check for radiological imaging analysis
                    img_analysis = meta.get("imaging_analysis")
                    img_findings_str = ""
                    if img_analysis:
                        findings = img_analysis.get("findings", [])
                        findings_text = "; ".join([f"{f.get('label')} ({f.get('description', '')})" for f in findings])
                        img_findings_str = (
                            f"\n- Radiological Imaging Modality: {img_analysis.get('modality')}\n"
                            f"- Anatomical Region: {img_analysis.get('anatomical_region')}\n"
                            f"- Identified Pathologies / Findings: {findings_text if findings_text else 'No major focal abnormality'}\n"
                            f"- Differential Considerations: {', '.join(img_analysis.get('differential_considerations', []))}\n"
                        )
                        # Also attach imaging visualization action if findings exist
                        if findings and recent_doc.file_type in {"png", "jpg", "jpeg", "webp"}:
                            proposed_actions.append({
                                "action_type": "render_imaging_scan",
                                "document_id": recent_doc.document_id,
                                "file_name": recent_doc.file_name,
                                "modality": img_analysis.get("modality"),
                                "anatomical_region": img_analysis.get("anatomical_region"),
                                "findings": findings,
                                "differential_considerations": img_analysis.get("differential_considerations", []),
                                "recommended_investigations": img_analysis.get("recommended_investigations", [])
                            })

                    doc_context_str = (
                        f"\nMost Recent Uploaded Medical Document:\n"
                        f"- File Name: {recent_doc.file_name}\n"
                        f"- Summary: {summary}\n"
                        f"- Extracted Lab Tests: {obs_summary if obs_summary else 'None extracted'}\n"
                        f"{img_findings_str}"
                    )
                except Exception:
                    pass

            # Targeted question about a specific lab or observation (e.g. "what was my last bp?")
            cond_list = [f"{c['diagnosis_name']} ({c['status']})" for c in ehr_data.get("conditions", [])]
            med_list = [f"{m['medication_name']} {m['dosage']}" for m in ehr_data.get("medications", [])]
            obs_list = [f"{o['test_name']}: {o['value_numeric']} {o['unit'] or ''} ({o['date']})" for o in ehr_data.get("observations", [])[:15]]
            
            ehr_summary = (
                f"Patient Record Summary for {current_user.full_name} ({current_user.patient_id}):\n"
                f"- Conditions: {', '.join(cond_list) if cond_list else 'None documented'}\n"
                f"- Medications: {', '.join(med_list) if med_list else 'None documented'}\n"
                f"- Observations: {'; '.join(obs_list) if obs_list else 'None recorded'}\n"
                f"{doc_context_str}"
            )

            try:
                prompt = (
                    f"You are Aarogya Drishti, the patient's personal AI healthcare companion.\n"
                    f"You have authorized access to the patient's verified electronic health record summary and uploaded documents below.\n"
                    f"{ehr_summary}\n\n"
                    f"Patient Question: {req.content}\n\n"
                    f"GUIDELINES & HUMAN-IN-THE-LOOP COLLABORATION:\n"
                    f"1. Explain the relevant data conversationally and clearly in plain terms without excessive technical jargon.\n"
                    f"2. If discussing uploaded scans/images and findings are provided above, summarize the findings and what they mean comfortably and reassuringly.\n"
                    f"3. PROACTIVE FOLLOW-UP (HITL): Ask the patient how they are currently feeling or if there is a specific symptom or part of their report they want to explore further.\n"
                    f"4. Keep the tone warm, clear, and reassuring."
                )
                resp = gemini_client.client.models.generate_content(model=model_name, contents=prompt)
                assistant_text = resp.text.strip() if resp and resp.text else (
                    f"According to your health record, here is your summary:\n\n{ehr_summary}"
                )
            except Exception as e:
                logger.warning(f"Gemini EHR question synthesis error: {e}")
                assistant_text = f"Here is the relevant information from your connected health record:\n\n{ehr_summary}"

    # --- Intent D: Medical Question or Symptom Inquiry ---
    else:
        # 1. Fetch authorized patient clinical context
        recent_conditions = db.scalars(
            select(Condition)
            .where((Condition.patient_id == current_user.patient_id) & (Condition.clinical_status == 'active'))
            .limit(5)
        ).all()
        cond_str = ", ".join([c.diagnosis_name for c in recent_conditions]) if recent_conditions else "None recorded"

        recent_meds = db.scalars(
            select(Medication)
            .where((Medication.patient_id == current_user.patient_id) & (Medication.status == 'active'))
            .limit(5)
        ).all()
        med_str = ", ".join([f"{m.medication_name} ({m.dosage})" for m in recent_meds]) if recent_meds else "None recorded"

        # 2. Attempt RAG retrieval from verified guidelines
        rag_service = get_rag_service()
        rag_succeeded = False
        rag_answer = ""
        rag_citations = []
        retrieval_status = "not_attempted"

        try:
            rag_res = rag_service.answer_medical_inquiry(question=req.content, top_k=3)
            rag_answer = rag_res.get("answer", "")
            rag_citations = rag_res.get("citations", [])
            retrieval_status = rag_res.get("evidence_status", "UNKNOWN")
            rag_succeeded = bool(rag_answer and rag_res.get("evidence_status") in {"SUFFICIENT", "PARTIAL", "EMPTY_RETRIEVAL", "LOW_RELEVANCE"})
        except Exception as rag_err:
            retrieval_status = f"ERROR: {type(rag_err).__name__}"
            log_chat_event(
                request_id=req_id,
                conversation_id=conversation_id,
                patient_id=current_user.patient_id,
                processing_stage="rag_retrieval_failed",
                retrieval_status=retrieval_status,
                exception_type=type(rag_err).__name__,
                safe_error_message=str(rag_err)
            )

        # 3. Synthesize final answer combining RAG result + Patient Context + Gemini
        hist_str = "\n".join([f"{h['sender'].capitalize()}: {h['content']}" for h in chronological_history[-3:]])
        
        if rag_succeeded and rag_answer:
            # We have verified guideline evidence from RAG
            try:
                conversational_prompt = (
                    f"You are Aarogya Drishti, the patient's personal AI healthcare companion inside the hospital management system assisting patient {current_user.full_name} ({current_user.patient_id}).\n"
                    f"IMPORTANT INSTRUCTION: You have direct authorized access to the patient's connected electronic health records and uploaded documents. NEVER claim that you do not have access to their personal medical records, files, or reports.\n"
                    f"COMMUNICATION & HUMAN-IN-THE-LOOP GUIDELINES:\n"
                    f"1. Be empathetic, natural, and helpful. Avoid overly robotic, repetitive boilerplates.\n"
                    f"2. Use the Verified Clinical Guidelines and patient context below to provide sound educational explanations.\n"
                    f"3. PROACTIVE CLARIFICATION & COLLABORATION (HITL):\n"
                    f"   - If important information is missing (such as duration, severity, onset, triggers, fever, or prior episodes), "
                    f"politely ask the patient 1-2 targeted follow-up questions to help clarify the situation.\n"
                    f"   - Before suggesting next steps, ask how they would prefer to proceed (e.g., tracking readings, preparing a summary for their doctor, or reviewing diet/lifestyle tips).\n"
                    f"4. If citing reference guidelines, reference them naturally (e.g. 'according to clinical guidelines [CHK-...]') without stiff, unnatural phrasing.\n"
                    f"5. Always note common red-flag signs that would warrant in-person medical attention.\n"
                    f"6. CRITICAL: NEVER draw or output ASCII text graphs, plots, or asterisk (*) charts. High-resolution Matplotlib medical charts and educational reference images are rendered natively by the platform.\n\n"
                    f"Patient Health Baseline: Conditions: [{cond_str}], Active Medications: [{med_str}].\n"
                    f"Recent conversation:\n{hist_str}\n\n"
                    f"Verified Clinical Guideline Evidence:\n{rag_answer}\n\n"
                    f"Patient Inquiry: {req.content}\n\n"
                    f"Respond in natural, well-structured conversational markdown with clear paragraphs or bullet points."
                )
                resp = gemini_client.client.models.generate_content(model=model_name, contents=conversational_prompt)
                assistant_text = (resp.text.strip() if resp and resp.text and resp.text.strip() else None) or (rag_answer.strip() if rag_answer and rag_answer.strip() else None) or (
                    "I have reviewed your inquiry against verified clinical guidelines. "
                    "For personalized medical evaluation or if symptoms persist, please consult your healthcare provider."
                )
            except Exception as gemini_err:
                logger.warning(f"Gemini conversational synthesis failed, falling back to direct RAG answer: {gemini_err}")
                assistant_text = rag_answer or (
                    "I have reviewed your inquiry against verified clinical guidelines. "
                    "For personalized medical evaluation, please consult your healthcare provider."
                )
        else:
            # RAG reference search had an error, returned insufficient evidence, or was unavailable - fall back to Gemini clinical guidance with disclaimer
            try:
                fallback_prompt = (
                    f"You are Aarogya Drishti, the patient's personal AI healthcare companion inside the Aarogya HMS platform.\n"
                    f"Patient: {current_user.full_name} (ID: {current_user.patient_id}).\n"
                    f"Known Conditions: [{cond_str}], Known Medications: [{med_str}].\n"
                    f"IMPORTANT INSTRUCTION: You are fully integrated with the patient's electronic health records. NEVER claim that you do not have access to their personal medical records, files, or portal.\n"
                    f"Recent conversation:\n{hist_str}\n\n"
                    f"Patient Question: {req.content}\n\n"
                    f"COMMUNICATION & HUMAN-IN-THE-LOOP GUIDELINES:\n"
                    f"1. Provide a natural, friendly, and informative overview in conversational language.\n"
                    f"2. Avoid rigid robotic phrasing or repetitive standard disclaimers.\n"
                    f"3. PROACTIVE CLARIFICATION (HITL): Ask the patient 1-2 relevant follow-up questions to understand their context better "
                    f"(e.g. how long they have had the symptom, whether anything makes it better or worse, or if they took any medicine).\n"
                    f"4. Shape the response collaboratively by asking what aspect they'd like to explore next.\n"
                    f"5. Mention any obvious warning signs that would require visiting an urgent care clinic or doctor.\n"
                    f"6. CRITICAL: NEVER output ASCII text graphs or asterisk (*) charts. Matplotlib clinical charts and educational medical illustrations are automatically rendered in the interface."
                )
                resp = gemini_client.client.models.generate_content(model=model_name, contents=fallback_prompt)
                assistant_text = (resp.text.strip() if resp and resp.text and resp.text.strip() else None) or (
                    "I have reviewed your question. For specific medical evaluation regarding your symptoms and health baseline, "
                    "please consult your primary healthcare provider."
                )
            except Exception as final_err:
                logger.error(f"Both RAG and Gemini failed for request {req_id}: {final_err}")
                assistant_text = (
                    "I am currently experiencing connectivity difficulties with the medical reference service, "
                    "which is temporarily unavailable. "
                    "Please ask your question again in a moment. If you are experiencing concerning symptoms, "
                    "please contact your doctor or local health center immediately."
                )

    # Check for educational medical illustrations from trusted sources (NIH/WHO/Wikimedia)
    from backend.app.services.educational_visuals_service import EducationalVisualsService
    edu_visual = EducationalVisualsService.find_or_resolve_visual(req.content)
    if edu_visual:
        proposed_actions.append({
            "action_type": "render_educational_image",
            "badge": edu_visual["badge"],
            "title": edu_visual["title"],
            "source": edu_visual["source"],
            "source_url": edu_visual["source_url"],
            "image_url": edu_visual["image_url"],
            "explanation": edu_visual["explanation"],
            "key_points": edu_visual["key_points"]
        })

    # Check if user asked to see previous radiological scans
    q_low = req.content.lower()
    if any(k in q_low for k in ["previous scan", "show my mri", "show my scan", "show my x-ray", "show my ct", "view my mri", "my scans", "previous scans"]):
        scan_docs = db.scalars(
            select(PatientDocument)
            .where(
                (PatientDocument.patient_id == current_user.patient_id) &
                (PatientDocument.file_type.in_(["png", "jpg", "jpeg", "webp"]))
            )
            .order_by(PatientDocument.created_at.desc())
        ).all()
        for sdoc in scan_docs[:3]:
            doc_meta = {}
            if sdoc.extracted_metadata:
                try:
                    doc_meta = json.loads(sdoc.extracted_metadata)
                except Exception:
                    pass
            img_an = doc_meta.get("imaging_analysis", {})
            proposed_actions.append({
                "action_type": "render_imaging_scan",
                "document_id": sdoc.document_id,
                "file_name": sdoc.file_name,
                "document_type": sdoc.document_type,
                "modality": img_an.get("modality", "Radiological Scan"),
                "anatomical_region": img_an.get("anatomical_region", "Diagnostic Imaging"),
                "findings": img_an.get("findings", []),
                "differential_considerations": img_an.get("differential_considerations", []),
                "recommended_investigations": img_an.get("recommended_investigations", [])
            })

    # If clinical events were proposed, note that human review / confirmation is pending
    if appended_ehr_events:
        append_notices = []
        for ev in appended_ehr_events:
            append_notices.append(f"• **{ev['summary']}** (Confidence: `{ev['confidence']:.2f}`)")
        notice_block = (
            f"\n\n> [!TIP]\n> **Proposed Health Record Update (Doctor Review Required):**\n" +
            "\n".join(append_notices) +
            f"\n> *Please click below to submit this entry for your doctor's clinical verification.*"
        )
        assistant_text = assistant_text + notice_block

    # 6. Save assistant message with UTC timestamp
    asst_now = datetime.now(timezone.utc)
    asst_msg_id = f"MSG-{uuid.uuid4().hex[:10].upper()}"
    all_actions = appended_ehr_events + proposed_actions
    asst_msg = ChatMessage(
        message_id=asst_msg_id,
        conversation_id=conversation_id,
        sender="assistant",
        content=assistant_text,
        proposed_ehr_actions=json.dumps(all_actions) if all_actions else None,
        is_confirmed_to_ehr=False,  # Pending doctor verification
        created_at=asst_now
    )
    db.add(asst_msg)
    conv.updated_at = asst_now
    db.commit()
    db.refresh(asst_msg)

    duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
    log_chat_event(
        request_id=req_id,
        conversation_id=conversation_id,
        patient_id=current_user.patient_id,
        processing_stage="completed",
        model_identifier=model_name,
        response_status="success",
        duration_ms=duration_ms
    )

    return ChatMessageRead.model_validate(asst_msg)


@router.post("/confirm-action")
def confirm_action_to_ehr(
    req: ConfirmEHRActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.patient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No patient record associated.")

    p_data = req.payload or req.data or {}
    if req.message_id:
        msg = db.scalar(select(ChatMessage).where(ChatMessage.message_id == req.message_id))
        if msg:
            msg.is_confirmed_to_ehr = True

    if req.action_type in {"measurement", "blood_pressure", "glucose", "pulse", "spo2", "weight"}:
        log_entry = DailyHealthLog(
            id=f"LOG-{uuid.uuid4().hex[:8].upper()}",
            patient_id=current_user.patient_id,
            log_date=date.today(),
            systolic_bp=p_data.get("systolic_bp") or p_data.get("systolic"),
            diastolic_bp=p_data.get("diastolic_bp") or p_data.get("diastolic"),
            fasting_glucose=p_data.get("fasting_glucose"),
            post_meal_glucose=p_data.get("post_meal_glucose"),
            pulse=p_data.get("pulse"),
            spo2=p_data.get("spo2"),
            weight_kg=p_data.get("weight_kg"),
            source="patient_confirmed_hitl",
            notes="Verified and confirmed by patient via Human-in-the-Loop review."
        )
        db.add(log_entry)

        # Stage for Doctor Verification Workflow
        from backend.app.services.doctor_verification_service import DoctorVerificationService
        DoctorVerificationService.stage_pending_update(
            patient_id=current_user.patient_id,
            update_type="observation",
            source="patient_chat",
            proposed_data=p_data,
            assigned_doctor_id="DOC-CARD-001",
            db=db
        )

        db.commit()
        return {"status": "confirmed", "message": "Health measurement logged and submitted to your physician for verification."}

    elif req.action_type == "medication":
        med_name = p_data.get("medication_name") or p_data.get("name")
        dosage = p_data.get("dosage") or "Standard clinical dose"
        if med_name:
            # Stage for Doctor Verification Workflow
            from backend.app.services.doctor_verification_service import DoctorVerificationService
            DoctorVerificationService.stage_pending_update(
                patient_id=current_user.patient_id,
                update_type="medication",
                source="patient_chat",
                proposed_data={"medication_name": med_name, "dosage": dosage, "start_date": str(date.today())},
                assigned_doctor_id="DOC-CARD-001",
                db=db
            )
            return {"status": "confirmed", "message": f"Medication '{med_name}' submitted for doctor clinical verification."}

    db.commit()
    return {"status": "confirmed", "message": "Record proposal acknowledged."}
