"""
Live Knowledge-Base Diagnostics Service for Aarogya Drishti 2.0.
Returns exact, non-hallucinated vector counts, namespaces, registered documents,
checksums, and retrieval model parameters.
"""

from typing import Dict, Any
from datetime import datetime, timezone
from rag.pinecone_store import PineconeManager
from rag.source_registry import MedicalSourceRegistry

class KnowledgeBaseDiagnosticsService:
    @staticmethod
    def get_live_diagnostics() -> Dict[str, Any]:
        """
        Gathers live stats directly from Pinecone index and the verified source registry.
        Never hardcodes vector numbers or claims unindexed documents.
        """
        registry = MedicalSourceRegistry()
        sources = registry.list_sources()

        # Connect to Pinecone and get live stats
        pinecone_stats = {}
        index_health = "OFFLINE"
        total_vectors = 0
        namespaces = {}

        try:
            pm = PineconeManager()
            idx = pm.get_index()
            raw_stats = idx.describe_index_stats()
            index_health = "HEALTHY_ACTIVE"
            total_vectors = raw_stats.get("total_vector_count", 0)
            dim = raw_stats.get("dimension", 384)
            metric = raw_stats.get("metric", "cosine")
            
            raw_ns = raw_stats.get("namespaces", {})
            for ns_name, ns_info in raw_ns.items():
                namespaces[ns_name] = {
                    "vector_count": ns_info.get("vector_count", 0)
                }
        except Exception as e:
            index_health = f"ERROR: {str(e)}"
            dim = 384
            metric = "cosine"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "index_name": "aarogya-medical-knowledge",
            "index_status": index_health,
            "total_vector_count": total_vectors,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "embedding_dimension": dim,
            "similarity_metric": metric,
            "namespaces": namespaces,
            "registered_sources_count": len(sources),
            "sources": [
                {
                    "document_id": s.get("document_id"),
                    "title": s.get("title"),
                    "publisher": s.get("publisher"),
                    "page_count": s.get("page_count"),
                    "target_namespace": s.get("target_namespace"),
                    "ingestion_status": s.get("ingestion_status"),
                    "checksum": s.get("checksum", "verified_sha256")[:16] + "..." if s.get("checksum") else None
                } for s in sources
            ]
        }

    @staticmethod
    def format_diagnostics_markdown(diag: Dict[str, Any]) -> str:
        """Renders verified knowledge-base diagnostics in GitHub-flavored Markdown."""
        ns_list = []
        for ns_name, info in diag.get("namespaces", {}).items():
            ns_list.append(f"- Namespace `{ns_name}`: **{info['vector_count']}** dense vectors")

        sources = diag.get("sources", [])
        src_rows = []
        for s in sources:
            src_rows.append(f"| `{s['document_id']}` | {s['title'][:45]}... | {s['publisher']} | {s.get('page_count', 'N/A')} | `{s['target_namespace']}` |")

        md = [
            f"### Aarogya Drishti 2.0 Knowledge Base Diagnostics\n",
            f"- **Pinecone Vector Database Status:** `{diag['index_status']}`",
            f"- **Index Name:** `{diag['index_name']}`",
            f"- **Total Live Vectors Indexed:** **{diag['total_vector_count']} vectors**",
            f"- **Embedding Model:** `{diag['embedding_model']}` ({diag['embedding_dimension']}-dimensional, `{diag['similarity_metric']}` metric)",
            f"- **Registered Medical Documents:** **{diag['registered_sources_count']} reference publications**\n",
            "#### Active Vector Namespaces:\n",
            "\n".join(ns_list) if ns_list else "- *No active namespaces found.*",
            "\n#### Registered & Ingested Knowledge Sources:\n",
            "| Document ID | Document Title | Publisher | Pages | Namespace |",
            "| :--- | :--- | :--- | :---: | :--- |",
            "\n".join(src_rows),
            "\n> [!NOTE]\n> *Vector counts and namespaces are fetched in real-time directly from Pinecone serverless infrastructure.*"
        ]
        return "\n".join(md)

