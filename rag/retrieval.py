"""
Multi-Namespace Medical Reference Semantic Retrieval Service
Features:
- Takes medical inquiry text
- Query understanding and keyword expansion
- Dense semantic retrieval across multiple verified namespaces:
    - 'medical-references-v2' (WHO, MedlinePlus, MoHFW, CDC guidelines)
    - 'medical-encyclopedia-v1' (The Gale Encyclopedia of Medicine)
    - 'medical-references-v1' (legacy core references)
- Source diversity and de-duplication
- Topic-aware filtering and Re-ranking by relevance
- Strict safety guard: NEVER queries or exposes patient EHR data in reference retrieval
"""

import time
import logging
from typing import List, Dict, Any, Optional

from rag.embeddings import MedicalEmbeddingService
from rag.pinecone_store import PineconeManager, DEFAULT_NAMESPACE

logger = logging.getLogger("MedicalRetrievalService")

SEARCH_NAMESPACES = [
    "medical-references-v2",
    "medical-encyclopedia-v1",
    "medical-references-v1"
]

class MedicalRetrievalService:

    def __init__(
        self,
        embedding_service: Optional[MedicalEmbeddingService] = None,
        pinecone_manager: Optional[PineconeManager] = None,
        namespaces: Optional[List[str]] = None
    ):
        self.embedding_service = embedding_service or MedicalEmbeddingService()
        self.pinecone_manager = pinecone_manager or PineconeManager()
        self.index = self.pinecone_manager.get_index()
        self.namespaces = namespaces or SEARCH_NAMESPACES

    @staticmethod
    def expand_query(query: str) -> List[str]:
        """
        Generates query variants for complex multi-topic or symptom queries.
        """
        variants = [query.strip()]
        lower = query.lower()
        
        # Medical synonym & related term expansion
        if "hba1c" in lower or "glycated hemoglobin" in lower:
            variants.append("glycated hemoglobin blood glucose diabetes monitoring")
        if "bp" in lower or "high blood pressure" in lower:
            variants.append("hypertension blood pressure systolic diastolic target guidelines")
        if "cough" in lower and "fever" in lower:
            variants.append("respiratory infection pneumonia influenza symptoms")
        if "rash" in lower or "itching" in lower:
            variants.append("dermatological eruption pruritus allergic contact dermatitis")
        if "uti" in lower or "urinary" in lower:
            variants.append("urinary tract infection dysuria cystitis")

        return variants[:2]

    def search(
        self,
        query: str,
        top_k: int = 5,
        topic_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute multi-namespace dense retrieval with diversity and duplicate elimination.
        """
        start_time = time.perf_counter()
        if not query or not query.strip():
            return {
                "query": query,
                "latency_ms": 0.0,
                "total_results": 0,
                "results": []
            }

        # 1. Expand query variants
        query_variants = self.expand_query(query)
        all_candidates = []
        seen_chunks = set()

        filter_dict = {"medical_topic": topic_filter.lower()} if topic_filter else None

        for q_text in query_variants:
            query_vector = self.embedding_service.embed_text(q_text)

            # Query each verified namespace to guarantee source diversity
            for ns in self.namespaces:
                try:
                    resp = self.index.query(
                        vector=query_vector,
                        top_k=top_k,
                        namespace=ns,
                        filter=filter_dict,
                        include_metadata=True
                    )
                    matches = resp.get("matches", [])
                    for match in matches:
                        cid = match.get("id")
                        if cid in seen_chunks:
                            continue
                        seen_chunks.add(cid)

                        meta = match.get("metadata", {})
                        source_org = meta.get("source_organization") or meta.get("publisher", "Verified Medical Guideline")
                        doc_title = meta.get("title") or meta.get("document_title", "Medical Reference")
                        
                        citation = f"{source_org} - {doc_title}"
                        if meta.get("page_number"):
                            citation += f", Page {meta.get('page_number')}"
                        elif meta.get("page_start"):
                            citation += f", Pages {meta.get('page_start')}-{meta.get('page_end', meta.get('page_start'))}"
                        elif meta.get("section_heading"):
                            citation += f", Section: {meta.get('section_heading')}"

                        all_candidates.append({
                            "chunk_id": cid,
                            "document_id": meta.get("document_id") or "DOC_REF",
                            "title": doc_title,
                            "source_organization": source_org,
                            "publisher": source_org,
                            "edition": meta.get("edition"),
                            "medical_topic": meta.get("medical_topic", "general_medicine"),
                            "section_heading": meta.get("section_heading", "General"),
                            "page_number": meta.get("page_number") or meta.get("page_start"),
                            "source_url": meta.get("source_url", "https://who.int"),
                            "citation": citation,
                            "similarity_score": round(match.get("score", 0.0), 4),
                            "content": meta.get("content", ""),
                            "namespace": ns
                        })
                except Exception as e:
                    logger.warning(f"Error querying namespace {ns}: {e}")

        # 2. Re-rank by similarity score
        all_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

        # 3. Source diversity: avoid one document dominating all top_k slots
        final_results = []
        doc_count = {}
        for cand in all_candidates:
            doc_id = cand["document_id"]
            if doc_count.get(doc_id, 0) >= 3:
                continue
            doc_count[doc_id] = doc_count.get(doc_id, 0) + 1
            final_results.append(cand)
            if len(final_results) >= top_k:
                break

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "query": query,
            "latency_ms": latency_ms,
            "total_results": len(final_results),
            "results": final_results
        }
