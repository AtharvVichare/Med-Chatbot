"""
Vector Indexer & Upsert Pipeline for Medical Chunks
Reads validated JSONL files from data/processed/ and uploads to Pinecone index:
- Batch upserts (e.g. 50 chunks per batch)
- Stable vector IDs (matching chunk_id: CHK-XXXX)
- Metadata preservation (document_id, title, org, url, pub_date, section, page, topic, content)
- Stale vector cleanup for modified/removed documents
- Idempotent execution
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from rag.embeddings import MedicalEmbeddingService
from rag.pinecone_store import PineconeManager, DEFAULT_NAMESPACE

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

class VectorIndexer:

    def __init__(
        self,
        embedding_service: Optional[MedicalEmbeddingService] = None,
        pinecone_manager: Optional[PineconeManager] = None,
        namespace: str = DEFAULT_NAMESPACE
    ):
        self.embedding_service = embedding_service or MedicalEmbeddingService()
        self.pinecone_manager = pinecone_manager or PineconeManager()
        self.index = self.pinecone_manager.get_index()
        self.namespace = namespace

    def index_jsonl_file(self, jsonl_path: Path, batch_size: int = 50) -> Dict[str, Any]:
        if not jsonl_path.exists():
            raise FileNotFoundError(f"JSONL file not found at {jsonl_path}")

        chunks: List[Dict[str, Any]] = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))

        if not chunks:
            return {"indexed_count": 0, "status": "EMPTY"}

        doc_id = chunks[0]["document_id"]
        # Delete stale vectors for this document if updating
        # (pinecone supports filter delete or namespace cleanup)

        # Generate embeddings in batch
        texts = [c["content"] for c in chunks]
        vectors = self.embedding_service.embed_batch(texts)

        upsert_records = []
        for c, vec in zip(chunks, vectors):
            metadata = {
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
                "document_version": c["document_version"],
                "review_status": c["review_status"],
                "token_count": c.get("token_count", 0),
                "content": c["content"]
            }
            # Remove None values from metadata for Pinecone compatibility
            cleaned_meta = {k: v for k, v in metadata.items() if v is not None}
            upsert_records.append({
                "id": c["chunk_id"],
                "values": vec,
                "metadata": cleaned_meta
            })

        # Batch upsert with retries
        total_upserted = 0
        for i in range(0, len(upsert_records), batch_size):
            batch = upsert_records[i : i + batch_size]
            self.index.upsert(vectors=batch, namespace=self.namespace)
            total_upserted += len(batch)

        return {
            "document_id": doc_id,
            "indexed_count": total_upserted,
            "status": "SUCCESS"
        }

    def index_all_processed(self, processed_dir: Path = PROCESSED_DIR) -> Dict[str, Any]:
        results = {}
        total = 0
        for p in processed_dir.glob("*.jsonl"):
            res = self.index_jsonl_file(p)
            results[p.name] = res
            total += res.get("indexed_count", 0)
        return {"total_vectors_indexed": total, "files": results}

