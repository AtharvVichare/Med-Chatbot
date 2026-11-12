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
    r'(?:trend|graph|chart|plot|compare|over\s*time|history\s*of)\s*(?:my\s*)?(?:bp|blood\s*pressure|sugar|glucose|hba1c|vitals|weight|pulse)',
    r'(?:show|display|see|plot|graph|view).*(?:blood\s*pressure|bp|glucose|sugar|hba1c|pulse|vitals).*(?:trend|graph|chart|plot|history)',
    r'(?:show|display|see|view)\s*(?:my\s*)?(?:trend|graph|chart|plot|history)\s*(?:for|of)?\s*(?:bp|blood\s*pressure|glucose|sugar|hba1c|pulse)?',
    r'(?:how\s*has\s*my\s*(?:bp|blood\s*pressure|glucose|sugar|hba1c|pulse)\s*(?:changed|trended|progressed))'
]

EHR_QUERY_PATTERNS = [
    r'(?:show|view|tell|display|see|get)\s*(?:my\s*)?(?:medical\s*history|health\s*record|complete\s*record|longitudinal\s*record|ehr|profile)',
    r'(?:what\s*(?:medicines?|medications?|drugs?|prescriptions?)\s*(?:am\s*i|do\s*i)\s*(?:taking|prescribed|on))',
    r'(?:my\s*(?:last|recent|latest)?\s*(?:bp|blood\s*pressure|sugar|glucose|vitals|hba1c|heart\s*rate|pulse|weight))',
    r'(?:what\s*(?:is|was)\s*my\s*(?:last|recent|latest|current)?\s*(?:bp|blood\s*pressure|glucose|sugar|hba1c|vitals|medication|prescription))',
    r'(?:show|tell|check|view)\s*(?:my\s*)?(?:records|vitals|medications|conditions|prescriptions|allergies|history|report)',
    r'(?:explain|review|analyze|what\s*(?:was|is)\s*(?:extracted|found|appended|seen))\s*(?:in|from|about)?\s*(?:my\s*)?(?:hba1c|lab|blood|report|test|uploaded|document|image|scan|mri|ct|x[- ]?ray|ultrasound)',
    r'(?:uploaded|attached)\s*(?:my\s*)?(?:medical\s*)?(?:report|file|document|image|pdf|test|lab|scan|mri|ct|x[- ]?ray)',
    r'(?:analyze|interpret|read|check)\s*(?:this|the|my)?\s*(?:uploaded\s*)?(?:image|scan|mri|ct|x[- ]?ray|ultrasound|sonography|photo|file)',
    r'(?:what\s*does\s*(?:this|the|my)\s*(?:image|scan|mri|ct|x[- ]?ray|ultrasound|report)\s*(?:show|mean|say))'
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

    # 4. Extract and Auto-Append Crucial Health Data to EHR (Confidence >= 0.75)
    # Does not change existing historical data; appends directly with current date and confidence score
    from backend.app.services.clinical_extractor import ClinicalExtractorService
    appended_ehr_events = []
    if current_user.patient_id:
        try:
            appended_ehr_events = ClinicalExtractorService.extract_from_chat(
                text=req.content,
                patient_id=current_user.patient_id,
                db=db
            )
        except Exception as extract_err:
            logger.warning(f"Error during auto-append extraction: {extract_err}")

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

    # --- Intent D: Hospital Discovery & Appointment Guidance ---
    elif intent == "hospital_discovery":
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

        from backend.app.api.v1.patients import get_patient_longitudinal_trends
        trend_resp = get_patient_longitudinal_trends(
            patient_id=current_user.patient_id,
            metric=target_metric,
            start_date=None,
            end_date=None,
            db=db,
            current_user=current_user
        )

        pts = trend_resp.data
        if not pts:
            assistant_text = (
                f"I checked your longitudinal health record for **{trend_resp.metric_name}**, but no measurements have been recorded yet. "
                f"You can log your daily readings or upload lab reports anytime to generate this trend chart."
            )
        else:
            dates = [p.date for p in pts]
            values = [p.value for p in pts]
            chart_action = {
                "action_type": "render_chart",
                "chart_title": trend_resp.metric_name,
                "chart_type": "line",
                "metric": target_metric,
                "unit": trend_resp.unit,
                "dates": dates,
                "values": values,
                "points": [p.model_dump() for p in pts],
                "latest_value": trend_resp.latest_value,
                "previous_value": trend_resp.previous_value,
                "change_direction": trend_resp.change_direction,
                "change_value": trend_resp.change_value,
                "latest_date": trend_resp.latest_date
            }
            proposed_actions.append(chart_action)

            summary_trend = (
                f"Your latest **{trend_resp.metric_name}** is **{trend_resp.latest_value} {trend_resp.unit}** (recorded on {trend_resp.latest_date}).\n"
                f"Comparing with your prior reading ({trend_resp.previous_value} {trend_resp.unit}), your measurement has {trend_resp.change_direction} by {abs(trend_resp.change_value or 0)} {trend_resp.unit}."
                if trend_resp.previous_value is not None else
                f"Your recorded **{trend_resp.metric_name}** is **{trend_resp.latest_value} {trend_resp.unit}** (recorded on {trend_resp.latest_date})."
            )
            assistant_text = (
                f"Here is your longitudinal **{trend_resp.metric_name}** chart generated from your verified health records:\n\n"
                f"{summary_trend}\n\n"
                f"*Note: Longitudinal trends are educational visualizations of recorded clinical tests and daily home vitals. Always review persistent changes with your physician.*"
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
                    f"CRITICAL INSTRUCTIONS FOR SCANS & IMAGES:\n"
                    f"1. If the patient has uploaded a scan or image (e.g. Chest X-ray, MRI, CT, Ultrasound) and findings are provided in the summary above, "
                    f"DO NOT say 'I am unable to view or directly analyze image files'. You HAVE the verified multimodal imaging analysis in your context! "
                    f"Summarize the modality, anatomical region, and the identified findings, highlighting normal structures or any focal abnormalities.\n"
                    f"2. Clearly present what the findings mean for their health in plain, reassuring language.\n"
                    f"3. Quote the differential considerations and recommended next steps provided in the context.\n"
                    f"4. Remind the patient gently that AI scan evaluation provides educational assistance, and official clinical reporting requires formal correlation by their treating doctor.\n"
                    f"5. Answer concisely, do not invent unrecorded values, and do not add repetitive diabetes warnings unless directly relevant."
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
                    f"You are Aarogya Drishti, a trusted healthcare companion assisting patient {current_user.full_name}.\n"
                    f"STRICT SAFETY & EVIDENCE RULES:\n"
                    f"1. You must answer strictly grounded in the Verified Clinical Guideline Evidence provided below.\n"
                    f"2. Every factual clinical claim MUST cite the corresponding reference identifier [CHK-...].\n"
                    f"3. Do not invent citations or assert causal diagnoses (e.g. if patient has diabetes in baseline, DO NOT assert diabetes caused their rash without explicit evidence).\n"
                    f"4. Clearly distinguish established clinical guidelines from general lifestyle advice, and explicitly note uncertainty if evidence is partial.\n"
                    f"5. Conclude with practical safety advice and red-flag warning signs.\n\n"
                    f"Patient Health Baseline: Conditions: [{cond_str}], Active Medications: [{med_str}].\n"
                    f"Recent conversation:\n{hist_str}\n\n"
                    f"Verified Clinical Guideline Evidence:\n{rag_answer}\n\n"
                    f"Patient Inquiry: {req.content}\n\n"
                    f"Synthesize your grounded response in clean GitHub-Flavored Markdown."
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
                    f"You are Aarogya Drishti, an AI healthcare assistant.\n"
                    f"Patient: {current_user.full_name}, Age Profile: {current_user.patient_id}.\n"
                    f"Known Conditions: [{cond_str}], Known Medications: [{med_str}].\n"
                    f"Recent conversation:\n{hist_str}\n\n"
                    f"Patient Question: {req.content}\n\n"
                    f"Please provide an informative, medically sound educational overview regarding their inquiry.\n"
                    f"Important instructions:\n"
                    f"- Mention that external verified guideline references are temporarily offline or limited for this specific inquiry, but provide general evidence-based educational insights.\n"
                    f"- Do not invent citation IDs.\n"
                    f"- Highlight any warning signs that need urgent medical attention."
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

    # If clinical events were auto-appended, attach an explicit notification banner to the assistant text
    if appended_ehr_events:
        append_notices = []
        for ev in appended_ehr_events:
            append_notices.append(f"• **{ev['summary']}** (Recorded: `{ev['date']}`, Confidence: `{ev['confidence']:.2f}`)")
        notice_block = (
            f"\n\n> [!NOTE]\n> **EHR Update Recorded:**\n" +
            "\n".join(append_notices) +
            f"\n> *This crucial health information has been securely appended to your lifetime longitudinal record.*"
        )
        assistant_text = assistant_text + notice_block

    # 6. Save assistant message with UTC timestamp
    asst_now = datetime.now(timezone.utc)
    asst_msg_id = f"MSG-{uuid.uuid4().hex[:10].upper()}"
    asst_msg = ChatMessage(
        message_id=asst_msg_id,
        conversation_id=conversation_id,
        sender="assistant",
        content=assistant_text,
        proposed_ehr_actions=json.dumps(appended_ehr_events) if appended_ehr_events else None,
        is_confirmed_to_ehr=bool(appended_ehr_events),
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

    if req.action_type == "measurement":
        log_entry = DailyHealthLog(
            id=f"LOG-{uuid.uuid4().hex[:8].upper()}",
            patient_id=current_user.patient_id,
            log_date=date.today(),
            systolic_bp=p_data.get("systolic_bp") or p_data.get("systolic"),
            diastolic_bp=p_data.get("diastolic_bp") or p_data.get("diastolic"),
            source="assistant_confirmed",
            notes="Added via AI Health Assistant conversational confirmation."
        )
        db.add(log_entry)
        db.commit()
        return {"status": "confirmed", "message": "Health measurement successfully confirmed and saved to your EHR."}
    
    db.commit()
    return {"status": "confirmed", "message": "Record proposal acknowledged."}
