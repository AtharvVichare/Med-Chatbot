"""
Comprehensive Batch Ingestion Pipeline for Gale Encyclopedia of Medicine (3rd Ed.)
Ingests core clinical pages (30 to 4065), skipping front matter (0-29) and back matter index (4066-4505).
Features:
- Incremental batching (default 50 pages per batch)
- Dense vector embeddings with all-MiniLM-L6-v2
- Persistent checkpointing in data/processed/checkpoints/gale_ingestion_checkpoint.json
- Direct upsert into Pinecone namespace 'medical-encyclopedia-v1'
- Resumable: can be interrupted and resumed at any time without duplicate vectors
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any

from rag.chunking import MedicalChunker
from rag.embeddings import MedicalEmbeddingService
from rag.vector_store import PineconeVectorStore
from rag.source_registry import MedicalSourceRegistry

CHECKPOINT_PATH = Path("data/processed/checkpoints/gale_ingestion_checkpoint.json")
CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)

PDF_PATH = "data/reference/guidelines/gale_encyclopedia_of_medicine_3rd_ed.pdf"
DOCUMENT_ID = "GALE-ENCYC-MED-3RD"
NAMESPACE = "medical-encyclopedia-v1"

# Skip front-matter and back-matter
START_PAGE = 30
END_PAGE = 4065

def load_checkpoint() -> Dict[str, Any]:
    if CHECKPOINT_PATH.exists():
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "document_id": DOCUMENT_ID,
        "last_processed_page": START_PAGE - 1,
        "total_chunks_upserted": 0,
        "status": "INITIALIZED",
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def save_checkpoint(last_page: int, total_chunks: int, status: str = "IN_PROGRESS"):
    data = {
        "document_id": DOCUMENT_ID,
        "last_processed_page": last_page,
        "total_chunks_upserted": total_chunks,
        "status": status,
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def run_batch_ingestion(batch_size: int = 50, max_pages: int = 500):
    print(f"=== Starting Gale Encyclopedia Batch Ingestion ===")
    print(f"PDF Source: {PDF_PATH}")
    print(f"Target Pages: {START_PAGE} to {END_PAGE} (Skipping 0-29 front matter & 4066-4505 index)")
    print(f"Namespace: {NAMESPACE}")

    checkpoint = load_checkpoint()
    current_page = max(START_PAGE, checkpoint["last_processed_page"] + 1)
    total_chunks = checkpoint["total_chunks_upserted"]

    print(f"Resuming from page: {current_page} (Total chunks already indexed: {total_chunks})")

    if current_page > END_PAGE:
        print("All clinical pages already ingested! Nothing to do.")
        return

    import pypdf
    reader = pypdf.PdfReader(PDF_PATH)
    total_pdf_pages = len(reader.pages)
    print(f"PDF successfully opened. Total pages in PDF: {total_pdf_pages}")

    chunker = MedicalChunker(chunk_size=750, chunk_overlap=120)
    embedding_service = MedicalEmbeddingService()
    vector_store = PineconeVectorStore()

    target_stop_page = min(current_page + max_pages - 1, END_PAGE)
    print(f"Job scope: processing pages {current_page} -> {target_stop_page}")

    while current_page <= target_stop_page:
        batch_end = min(current_page + batch_size - 1, target_stop_page)
        print(f"\nProcessing slice: pages {current_page} to {batch_end}...")

        batch_chunks: List[Dict[str, Any]] = []

        for p_num in range(current_page, batch_end + 1):
            try:
                page_obj = reader.pages[p_num]
                page_text = page_obj.extract_text() or ""
                if len(page_text.strip()) < 80:
                    continue  # Skip near-empty or blank spacer pages

                # Extract heading from first non-empty lines
                lines = [l.strip() for l in page_text.split("\n") if l.strip()]
                heading = lines[0] if lines else "Clinical Entry"
                if len(heading) > 80:
                    heading = heading[:80]

                # Chunk page content
                chunks = chunker.chunk_document(
                    text=page_text,
                    document_id=DOCUMENT_ID,
                    title="The Gale Encyclopedia of Medicine (3rd Ed.)",
                    source_organization="Gale Cengage Learning",
                    page_number=p_num + 1,
                    section_heading=heading,
                    topic="general_medicine"
                )
                batch_chunks.extend(chunks)
            except Exception as e:
                print(f"Warning: error reading page {p_num}: {e}")

        print(f"Generated {len(batch_chunks)} chunks for pages {current_page}-{batch_end}.")

        if batch_chunks:
            # Batch embedding
            texts = [c["content"] for c in batch_chunks]
            print(f"Embedding {len(texts)} chunks...")
            embeddings = embedding_service.embed_batch(texts, batch_size=32)

            # Prepare vectors for Pinecone
            vectors = []
            for c, emb in zip(batch_chunks, embeddings):
                vectors.append({
                    "id": c["chunk_id"],
                    "values": emb,
                    "metadata": {
                        "document_id": c["document_id"],
                        "chunk_id": c["chunk_id"],
                        "title": c.get("title", ""),
                        "page_number": c.get("page_number", 0),
                        "section_heading": c.get("section_heading", ""),
                        "source_organization": c.get("source_organization", ""),
                        "text": c.get("content", "")
                    }
                })

            # Upsert in batches of 100
            for i in range(0, len(vectors), 100):
                sub_vecs = vectors[i:i + 100]
                vector_store.upsert_vectors(vectors=sub_vecs, namespace=NAMESPACE)

            total_chunks += len(vectors)
            print(f"Successfully upserted {len(vectors)} vectors into namespace '{NAMESPACE}'. Total: {total_chunks}")

        current_page = batch_end + 1
        save_checkpoint(batch_end, total_chunks, "IN_PROGRESS" if current_page <= END_PAGE else "COMPLETED")

    print(f"\nBatch run complete! Processed up to page {batch_end}. Total vectors: {total_chunks}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gale Encyclopedia Batch Ingestion Worker")
    parser.add_argument("--batch-size", type=int, default=30, help="Pages per slice")
    parser.add_argument("--max-pages", type=int, default=150, help="Total pages to process in this run")
    args = parser.parse_args()

    run_batch_ingestion(batch_size=args.batch_size, max_pages=args.max_pages)

