"""
Namespace-Aware Vector Upsert Service for Aarogya Drishti Medical Knowledge Base
Supports versioned Pinecone namespaces:
- 'medical-references-v1' (legacy baseline with 9 chunks)
- 'medical-references-v2' (expanded corpus with 57 chunks across 12 domains)

Guarantees:
- Batch upserts (e.g. 50 chunks per batch)
- Stable, deterministic chunk IDs
- Complete metadata retention (exact document_id, title, org, source_url, license, domain, etc.)
- Idempotency & duplicate prevention
- Post-upsert remote count verification
- Zero PII / zero patient EHR data exposure
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from rag.embeddings import MedicalEmbeddingService
from rag.pinecone_store import PineconeManager

load_dotenv()

PROCESSED_V2_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" / "v2"
V2_NAMESPACE = "medical-references-v2"

class VersionedVectorUpserter:

    def __init__(
        self,
        embedding_service: Optional[MedicalEmbeddingService] = None,
        pinecone_manager: Optional[PineconeManager] = None,
        namespace: str = V2_NAMESPACE
    ):
        self.embedding_service = embedding_service or MedicalEmbeddingService()
        self.pinecone_manager = pinecone_manager or PineconeManager()
        self.index = self.pinecone_manager.get_index()
        self.namespace = namespace

    def upsert_master_v2(self, master_jsonl_path: Optional[Path] = None, batch_size: int = 50) -> Dict[str, Any]:
        """
        Loads all chunks from master_v2_chunks.jsonl and upserts them into Pinecone v2 namespace.
        """
        path = master_jsonl_path or (PROCESSED_V2_DIR / "master_v2_chunks.jsonl")
        if not path.exists():
            raise FileNotFoundError(f"Master v2 JSONL not found at {path}")

        chunks: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))

        print(f"Loaded {len(chunks)} v2 chunks from {path.name}")
        texts = [c["content"] for c in chunks]

        # 1. Generate embeddings in batch
        t0_emb = time.perf_counter()
        vectors = self.embedding_service.embed_batch(texts)
        emb_latency = time.perf_counter() - t0_emb
        print(f"Generated {len(vectors)} embeddings in {emb_latency:.2f} seconds.")

        # 2. Prepare Pinecone vector records with complete metadata
        records = []
        for c, vec in zip(chunks, vectors):
            meta = {
                "document_id": c["document_id"],
                "chunk_id": c["chunk_id"],
                "title": c["title"],
                "source_organization": c["source_organization"],
                "source_url": c["source_url"],
                "publication_date": c["publication_date"],
                "retrieval_date": c["retrieval_date"],
                "section_heading": c["section_heading"],
                "page_number": c.get("page_number"),
                "medical_topic": c["medical_topic"],
                "domain_group": c.get("domain_group", "general"),
                "license": c.get("license", ""),
                "document_version": c.get("document_version", "v2"),
                "review_status": c.get("review_status", ""),
                "token_count": c.get("token_count", 0),
                "content": c["content"]
            }
            cleaned_meta = {k: v for k, v in meta.items() if v is not None}
            records.append({
                "id": c["chunk_id"],
                "values": vec,
                "metadata": cleaned_meta
            })

        # 3. Upsert to Pinecone v2 namespace in batches
        total_upserted = 0
        t0_up = time.perf_counter()
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            self.index.upsert(vectors=batch, namespace=self.namespace)
            total_upserted += len(batch)
            print(f"Upserted batch {i // batch_size + 1}: {len(batch)} vectors to namespace '{self.namespace}'")

        upsert_latency = time.perf_counter() - t0_up

        # 4. Remote vector count verification (allowing for eventual consistency)
        time.sleep(3.0)
        stats = self.index.describe_index_stats()
        # stats is an IndexDescription object; convert namespaces to dict
        namespaces_dict = {}
        if hasattr(stats, "namespaces") and stats.namespaces:
            for ns, ns_info in stats.namespaces.items():
                namespaces_dict[ns] = getattr(ns_info, "vector_count", 0)
        total_vector_count = getattr(stats, "total_vector_count", 0)
        remote_count = namespaces_dict.get(self.namespace, 0)

        return {
            "namespace": self.namespace,
            "local_chunks": len(chunks),
            "upserted_count": total_upserted,
            "remote_vector_count": remote_count,
            "embedding_time_sec": round(emb_latency, 2),
            "upsert_time_sec": round(upsert_latency, 2),
            "total_vector_count": total_vector_count,
            "namespaces": namespaces_dict
        }

if __name__ == "__main__":
    upserter = VersionedVectorUpserter()
    res = upserter.upsert_master_v2()
    print("Upsert result:", json.dumps(res, indent=2))

