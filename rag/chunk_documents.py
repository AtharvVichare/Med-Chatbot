"""
Token-Aware Medical Document Chunking Pipeline
Implements:
- True token-based splitting via tiktoken (cl100k_base or o200k_base) matching ~500 tokens with 75 tokens overlap.
- Deterministic chunk ID generation: SHA-256(doc_id + section_heading + page_num + chunk_index)
- Strict metadata preservation:
    chunk_id, document_id, title, source_organization, source_url,
    publication_date, retrieval_date, section_heading, page_number,
    medical_topic, document_version, review_status, token_count
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.sources import MedicalSourceMetadata, get_source_metadata

class MedicalChunker:

    def __init__(
        self,
        target_tokens: int = 500,
        overlap_tokens: int = 75,
        encoding_name: str = "cl100k_base"
    ):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.tokenizer = tiktoken.get_encoding(encoding_name)
        
        # Configure recursive splitter using token length function
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.target_tokens,
            chunk_overlap=self.overlap_tokens,
            length_function=self.token_length,
            separators=["\n\n### ", "\n\n## ", "\n\n# ", "\n\n", "\n", ". ", " ", ""]
        )

    def token_length(self, text: str) -> int:
        return len(self.tokenizer.encode(text, disallowed_special=()))

    def generate_chunk_id(
        self,
        document_id: str,
        section_heading: str,
        page_number: Optional[int],
        chunk_index: int,
        content_hash: str
    ) -> str:
        unique_seed = f"{document_id}:{section_heading}:{page_number or 0}:{chunk_index}:{content_hash[:16]}"
        return f"CHK-{hashlib.sha256(unique_seed.encode('utf-8')).hexdigest()[:16].upper()}"

    def chunk_section(
        self,
        document_id: str,
        section_heading: str,
        text_content: str,
        page_number: Optional[int],
        source_meta: MedicalSourceMetadata,
        retrieval_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not text_content or not text_content.strip():
            return []

        chunks_text = self.splitter.split_text(text_content.strip())
        chunk_records = []
        retrieval_dt = retrieval_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for idx, chunk_str in enumerate(chunks_text):
            chunk_tokens = self.token_length(chunk_str)
            chunk_content_hash = hashlib.sha256(chunk_str.encode("utf-8")).hexdigest()
            chunk_id = self.generate_chunk_id(
                document_id=document_id,
                section_heading=section_heading,
                page_number=page_number,
                chunk_index=idx,
                content_hash=chunk_content_hash
            )

            record = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "title": source_meta.title,
                "source_organization": source_meta.organization,
                "source_url": source_meta.source_url,
                "publication_date": source_meta.publication_date,
                "retrieval_date": retrieval_dt,
                "section_heading": section_heading or "General",
                "page_number": page_number,
                "medical_topic": source_meta.topic,
                "document_version": source_meta.document_version,
                "review_status": source_meta.review_status,
                "token_count": chunk_tokens,
                "content": chunk_str
            }
            chunk_records.append(record)

        return chunk_records

def save_chunks_to_jsonl(chunks: List[Dict[str, Any]], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

