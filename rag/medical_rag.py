"""
End-to-End Medical RAG Pipeline for Aarogya Drishti.
Coordinates:
1. Input screening and emergency red-flag detection (MedicalSafetyEngine)
2. Local embedding generation (MedicalEmbeddingService)
3. Pinecone semantic vector retrieval (MedicalRetrievalService)
4. Evidence sufficiency & relevance threshold evaluation
5. Grounded prompt generation (MedicalPromptBuilder)
6. Gemini 3.5 Flash Lite synthesis (GeminiClient)
7. Citation cross-validation against retrieved chunks (CitationValidator)
8. Structured clinical output generation with standard disclaimers
"""

import time
import logging
from typing import Dict, Any, Optional, List

from rag.safety import MedicalSafetyEngine
from rag.retrieval import MedicalRetrievalService
from rag.prompt_builder import MedicalPromptBuilder, SYSTEM_INSTRUCTION
from rag.gemini_client import GeminiClient
from rag.citation_validator import CitationValidator

logger = logging.getLogger("AarogyaMedicalRAG")

# Minimum cosine similarity threshold to consider evidence relevant
DEFAULT_SIMILARITY_THRESHOLD = 0.38

CLINICAL_DISCLAIMER = (
    "NOTICE: Aarogya Drishti Medical Reference Assistant provides synthesis of published clinical "
    "guidelines and health topics for informational purposes only. It does not provide medical diagnoses, "
    "prescriptions, or individualized treatment plans. Always consult a qualified healthcare provider for clinical decisions."
)

class MedicalRAGService:
    def __init__(
        self,
        retrieval_service: Optional[MedicalRetrievalService] = None,
        gemini_client: Optional[GeminiClient] = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ):
        self.retrieval_service = retrieval_service or MedicalRetrievalService()
        self.gemini_client = gemini_client or GeminiClient()
        self.similarity_threshold = similarity_threshold

    def answer_medical_inquiry(
        self,
        question: str,
        top_k: int = 3,
        topic_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end grounded RAG inquiry.
        """
        overall_t0 = time.perf_counter()

        # Step 1: Input Screening & Emergency Detection
        safety_assessment = MedicalSafetyEngine.screen_question(question)
        safety_flags = safety_assessment["safety_flags"]
        emergency_directive = safety_assessment.get("emergency_directive")

        if not safety_assessment["safe_to_process"]:
            return {
                "question": question,
                "answer": "Your request could not be processed because it triggered safety policies regarding prompt injection or unauthorized instructions.",
                "evidence_status": "BLOCKED_BY_SAFETY",
                "safety_flags": safety_flags,
                "citations": [],
                "rejected_citations": [],
                "emergency_directive": None,
                "disclaimer": CLINICAL_DISCLAIMER,
                "model_id": self.gemini_client.model_name,
                "retrieval_latency_ms": 0.0,
                "generation_latency_ms": 0.0,
                "total_latency_ms": round((time.perf_counter() - overall_t0) * 1000, 2)
            }

        # Step 2: Semantic Retrieval from Pinecone
        t_ret_start = time.perf_counter()
        retrieval_resp = self.retrieval_service.search(
            query=question,
            top_k=top_k,
            topic_filter=topic_filter
        )
        retrieval_latency_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)
        raw_matches = retrieval_resp.get("results", [])

        # Filter matches by similarity threshold & format for prompt builder
        retrieved_chunks = []
        max_score = 0.0
        for m in raw_matches:
            score = m.get("similarity_score", 0.0)
            if score > max_score:
                max_score = score
            if score >= self.similarity_threshold:
                retrieved_chunks.append({
                    "chunk_id": m.get("chunk_id"),
                    "document_id": m.get("document_id") or m.get("title", "REF_DOC").replace(" ", "_").upper()[:16],
                    "title": m.get("title"),
                    "source_organization": m.get("source_organization"),
                    "source_url": m.get("source_url"),
                    "page_number": m.get("page_number"),
                    "section_heading": m.get("section_heading"),
                    "text": m.get("content", ""),
                    "score": score
                })

        # Step 3: Assess Evidence Sufficiency
        evidence_status = "SUFFICIENT"
        if not retrieved_chunks or max_score < self.similarity_threshold:
            evidence_status = "INSUFFICIENT_EVIDENCE"

        # If emergency detected, prioritize emergency warning but still attach relevant references if available
        if safety_flags.get("is_emergency"):
            ans = f"{emergency_directive}\n\nClinical Reference Context: Please seek immediate emergency medical care."
            return {
                "question": question,
                "answer": ans,
                "evidence_status": "EMERGENCY_ESCALATION",
                "safety_flags": safety_flags,
                "citations": [],
                "rejected_citations": [],
                "emergency_directive": emergency_directive,
                "disclaimer": CLINICAL_DISCLAIMER,
                "model_id": self.gemini_client.model_name,
                "retrieval_latency_ms": retrieval_latency_ms,
                "generation_latency_ms": 0.0,
                "total_latency_ms": round((time.perf_counter() - overall_t0) * 1000, 2)
            }

        # If evidence is insufficient, abstain gracefully without sending hallucination-prone prompt to Gemini
        if evidence_status == "INSUFFICIENT_EVIDENCE":
            ans = (
                "Insufficient clinical evidence in Aarogya Drishti's reference guidelines to answer this inquiry accurately. "
                "The current reference library focuses specifically on diabetes, hypertension, and cardiovascular risk."
            )
            return {
                "question": question,
                "answer": ans,
                "evidence_status": "INSUFFICIENT_EVIDENCE",
                "safety_flags": safety_flags,
                "citations": [],
                "rejected_citations": [],
                "emergency_directive": None,
                "disclaimer": CLINICAL_DISCLAIMER,
                "model_id": self.gemini_client.model_name,
                "retrieval_latency_ms": retrieval_latency_ms,
                "generation_latency_ms": 0.0,
                "total_latency_ms": round((time.perf_counter() - overall_t0) * 1000, 2)
            }

        # Step 4: Build Prompt & Call Gemini
        prompt = MedicalPromptBuilder.build_prompt(question, retrieved_chunks)
        t_gen_start = time.perf_counter()
        gemini_result = self.gemini_client.generate_clinical_response(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1
        )
        generation_latency_ms = round((time.perf_counter() - t_gen_start) * 1000, 2)

        if not gemini_result.get("success"):
            return {
                "question": question,
                "answer": f"Unable to generate response at this time: {gemini_result.get('error')}",
                "evidence_status": "GENERATION_ERROR",
                "safety_flags": safety_flags,
                "citations": [],
                "rejected_citations": [],
                "emergency_directive": None,
                "disclaimer": CLINICAL_DISCLAIMER,
                "model_id": self.gemini_client.model_name,
                "retrieval_latency_ms": retrieval_latency_ms,
                "generation_latency_ms": generation_latency_ms,
                "total_latency_ms": round((time.perf_counter() - overall_t0) * 1000, 2)
            }

        gen_data = gemini_result.get("data", {})
        answer_text = gen_data.get("summary", "")
        raw_citations = gen_data.get("citations", [])

        # Step 5: Citation Cross-Validation
        valid_citations, rejected_citations = CitationValidator.validate_citations(
            model_citations=raw_citations,
            retrieved_chunks=retrieved_chunks
        )

        # Fallback: If Gemini generated an answer but failed to structure citations, attach retrieved chunk metadata
        if not valid_citations and retrieved_chunks:
            for c in retrieved_chunks:
                valid_citations.append({
                    "document_id": c["document_id"],
                    "chunk_id": c["chunk_id"],
                    "title": c["title"],
                    "source_organization": c["source_organization"],
                    "source_url": c["source_url"],
                    "page_number": c.get("page_number"),
                    "section_heading": c.get("section_heading"),
                    "verification_status": "VERIFIED_RETRIEVED"
                })

        total_latency_ms = round((time.perf_counter() - overall_t0) * 1000, 2)

        return {
            "question": question,
            "answer": answer_text,
            "evidence_status": evidence_status,
            "safety_flags": safety_flags,
            "citations": valid_citations,
            "rejected_citations": rejected_citations,
            "emergency_directive": None,
            "disclaimer": CLINICAL_DISCLAIMER,
            "model_id": self.gemini_client.model_name,
            "retrieval_latency_ms": retrieval_latency_ms,
            "generation_latency_ms": generation_latency_ms,
            "total_latency_ms": total_latency_ms
        }

