"""
Contextual Overlapping Chunking Engine for Medical Reference Books & Documents
Supports:
- PDF page-by-page extraction via PyMuPDF (fitz)
- Artifact/Header/Footer removal and hyphenation stitching
- Hierarchical document structure (Document -> Section -> Heading -> Paragraph)
- Token-based overlapping chunking (Target 700 tokens, 120 token overlap, 100 min)
- Deterministic chunk hashing & checkpointing
- Rich contextualized embedding prefixes:
    Document: {title}
    Chapter/Section: {section}
    Topic: {topic}
    Passage: {text}
"""

import os
import re
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional, Generator
import fitz  # PyMuPDF

logger = logging.getLogger("ContextualChunkingEngine")

class ContextualChunkingEngine:
    def __init__(
        self,
        target_tokens: int = 700,
        overlap_tokens: int = 120,
        min_tokens: int = 100,
        checkpoint_dir: str = "data/processed/checkpoints"
    ):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic estimation of tokens based on whitespace and punctuation."""
        return max(1, len(re.findall(r"\w+|[^\w\s]", text)))

    @staticmethod
    def clean_text_artifacts(raw_text: str) -> str:
        """
        Removes recurring header/footer artifacts, fixes line-break hyphenations,
        and standardizes whitespace.
        """
        # Remove recurring page markers
        cleaned = re.sub(r'G\s*A\s*L\s*E\s*E\s*N\s*C\s*Y\s*C\s*L\s*O\s*P\s*E\s*D\s*I\s*A\s*O\s*F\s*M\s*E\s*D\s*I\s*C\s*I\s*N\s*E', '', raw_text, flags=re.IGNORECASE)
        # Fix hyphenated words across line breaks (e.g., 'hyperten- \nsion' -> 'hypertension')
        cleaned = re.sub(r'(\b[a-zA-Z]+)-\s*\n\s*([a-zA-Z]+\b)', r'\1\2', cleaned)
        # Normalize newlines and spaces
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    def extract_pdf_pages(
        self,
        pdf_path: str,
        start_page: int = 0,
        end_page: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Extracts pages from PDF preserving 1-based page numbers and metadata.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF source not found at: {pdf_path}")

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        limit_page = end_page if end_page is not None else total_pages
        limit_page = min(limit_page, total_pages)

        for page_idx in range(start_page, limit_page):
            page_num = page_idx + 1
            try:
                page = doc[page_idx]
                raw_text = page.get_text("text")
                cleaned_text = self.clean_text_artifacts(raw_text)
                
                # Check for blocks to extract section headers
                blocks = page.get_text("blocks")
                detected_headings = []
                for b in blocks:
                    block_text = b[4].strip()
                    if block_text and len(block_text) < 60 and '\n' not in block_text:
                        # Common section headers in medical reference encyclopedias
                        if block_text in {"Definition", "Description", "Causes and symptoms", "Diagnosis", "Treatment", "Prognosis", "Prevention", "Key terms", "Resources"}:
                            detected_headings.append(block_text)
                        elif block_text.isupper() or block_text.istitle():
                            detected_headings.append(block_text)

                yield {
                    "page_number": page_num,
                    "page_index": page_idx,
                    "raw_text": raw_text,
                    "cleaned_text": cleaned_text,
                    "detected_headings": detected_headings,
                    "has_text": bool(cleaned_text and len(cleaned_text) > 30)
                }
            except Exception as e:
                logger.error(f"Failed to extract page {page_num} of {pdf_path}: {e}")
                yield {
                    "page_number": page_num,
                    "page_index": page_idx,
                    "raw_text": "",
                    "cleaned_text": "",
                    "detected_headings": [],
                    "has_text": False,
                    "error": str(e)
                }

    def chunk_document_stream(
        self,
        document_id: str,
        document_title: str,
        publisher: str,
        edition: str,
        source_url: str,
        page_stream: Generator[Dict[str, Any], None, None],
        default_topic: str = "general_medicine"
    ) -> List[Dict[str, Any]]:
        """
        Consumes page stream and creates deterministic contextual chunks with overlap.
        """
        accumulated_tokens = []
        token_meta = []  # parallel list storing (page_number, current_heading, current_topic)
        current_heading = "General"
        current_topic = default_topic

        all_chunks = []
        chunk_sequence = 0

        for page in page_stream:
            if not page["has_text"]:
                continue

            page_num = page["page_number"]
            cleaned_text = page["cleaned_text"]

            # Update heading if new ones detected
            if page.get("detected_headings"):
                current_heading = page["detected_headings"][0]
                # If heading looks like a topic name, use it
                if len(page["detected_headings"]) > 1:
                    current_topic = page["detected_headings"][1].lower().replace(" ", "_")

            # Split into paragraph tokens preserving structure
            words = cleaned_text.split()
            for w in words:
                accumulated_tokens.append(w)
                token_meta.append((page_num, current_heading, current_topic))

            # When accumulated tokens reach target, emit chunk with overlap
            while len(accumulated_tokens) >= self.target_tokens:
                chunk_words = accumulated_tokens[:self.target_tokens]
                chunk_slice_meta = token_meta[:self.target_tokens]

                start_page = chunk_slice_meta[0][0]
                end_page = chunk_slice_meta[-1][0]
                sec_heading = chunk_slice_meta[0][1]
                top = chunk_slice_meta[0][2]

                passage_text = " ".join(chunk_words)
                token_count = len(chunk_words)

                # Deterministic chunk ID
                content_checksum = hashlib.sha256(passage_text.encode("utf-8")).hexdigest()
                chunk_id = f"CHK-GALE-{content_checksum[:12].upper()}"

                contextual_embedding_text = (
                    f"Document: {document_title} ({edition})\n"
                    f"Publisher: {publisher}\n"
                    f"Section/Entry: {sec_heading}\n"
                    f"Topic: {top}\n"
                    f"Passage:\n{passage_text}"
                )

                all_chunks.append({
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "title": document_title,
                    "publisher": publisher,
                    "source_organization": publisher,
                    "edition": edition,
                    "section_heading": sec_heading,
                    "medical_topic": top,
                    "page_start": start_page,
                    "page_end": end_page,
                    "page_number": start_page,
                    "chunk_sequence": chunk_sequence,
                    "token_count": token_count,
                    "content": passage_text,
                    "contextual_embedding_text": contextual_embedding_text,
                    "content_checksum": content_checksum,
                    "source_url": source_url
                })
                chunk_sequence += 1

                # Step forward sliding window by (target_tokens - overlap_tokens)
                step = self.target_tokens - self.overlap_tokens
                accumulated_tokens = accumulated_tokens[step:]
                token_meta = token_meta[step:]

        # Handle remaining tokens if greater than min_tokens
        if len(accumulated_tokens) >= self.min_tokens:
            start_page = token_meta[0][0]
            end_page = token_meta[-1][0]
            sec_heading = token_meta[0][1]
            top = token_meta[0][2]
            passage_text = " ".join(accumulated_tokens)

            content_checksum = hashlib.sha256(passage_text.encode("utf-8")).hexdigest()
            chunk_id = f"CHK-GALE-{content_checksum[:12].upper()}"
            contextual_embedding_text = (
                f"Document: {document_title} ({edition})\n"
                f"Publisher: {publisher}\n"
                f"Section/Entry: {sec_heading}\n"
                f"Topic: {top}\n"
                f"Passage:\n{passage_text}"
            )

            all_chunks.append({
                "chunk_id": chunk_id,
                "document_id": document_id,
                "title": document_title,
                "publisher": publisher,
                "source_organization": publisher,
                "edition": edition,
                "section_heading": sec_heading,
                "medical_topic": top,
                "page_start": start_page,
                "page_end": end_page,
                "page_number": start_page,
                "chunk_sequence": chunk_sequence,
                "token_count": len(accumulated_tokens),
                "content": passage_text,
                "contextual_embedding_text": contextual_embedding_text,
                "content_checksum": content_checksum,
                "source_url": source_url
            })

        return all_chunks

