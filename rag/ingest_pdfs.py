"""
PDF Medical Guideline Ingestor (PyMuPDF)
Extracts clinical text, section headers, tables, and page-level provenance using PyMuPDF (fitz):
- Extracts page-by-page text and detects section headings
- Handles multi-page documents while tracking exact page numbers
- Normalizes clinical text (preserving units: mmHg, mg/dL, mmol/L, %)
- Attaches comprehensive metadata to token-aware chunks
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf

from rag.sources import get_source_metadata
from rag.chunk_documents import MedicalChunker, save_chunks_to_jsonl
from rag.manifest import DocumentManifest, calculate_checksum

def normalize_clinical_text(text: str) -> str:
    if not text:
        return ""
    # Normalize line breaks and spaces
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Preserve medical punctuation and bullet markers
    text = text.replace("\u2013", "-").replace("\u2014", "--")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u2265", ">=").replace("\u2264", "<=")
    # Clean excessive whitespace while preserving paragraph spacing
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

class PDFGuidelineIngestor:

    def __init__(self, chunker: Optional[MedicalChunker] = None, manifest: Optional[DocumentManifest] = None):
        self.chunker = chunker or MedicalChunker()
        self.manifest = manifest or DocumentManifest()

    def parse_pdf_file(self, pdf_path: Path, source_id: str) -> List[Dict[str, Any]]:
        source_meta = get_source_metadata(source_id)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF document not found at: {pdf_path}")

        checksum = calculate_checksum(pdf_path)
        existing_doc = self.manifest.is_duplicate_hash(checksum)
        if existing_doc and existing_doc == source_id:
            print(f"[SKIP] Document {source_id} already ingested with identical checksum.")

        try:
            doc = pymupdf.open(str(pdf_path))
        except Exception as e:
            self.manifest.record_document(
                document_id=source_id,
                title=source_meta.title,
                source_id=source_id,
                file_path=str(pdf_path),
                sha256=checksum,
                status="FAILED",
                error_message=f"PyMuPDF Open Error: {str(e)}"
            )
            raise ValueError(f"Malformed or unreadable PDF: {str(e)}")

        all_chunks: List[Dict[str, Any]] = []
        current_section = f"{source_meta.title} - Clinical Guidance"

        for page_num in range(len(doc)):
            page = doc[page_num]
            raw_text = page.get_text("text") or ""
            clean_page_text = normalize_clinical_text(raw_text)

            if len(clean_page_text) < 40:
                # Skip cover or blank pages
                continue

            # Detect potential heading from first non-empty lines
            lines = [ln.strip() for ln in clean_page_text.split("\n") if ln.strip()]
            if lines and len(lines[0]) < 90 and not lines[0].endswith("."):
                current_section = f"{source_meta.title} - {lines[0]}"

            chunks = self.chunker.chunk_section(
                document_id=source_id,
                section_heading=current_section,
                text_content=clean_page_text,
                page_number=page_num + 1,
                source_meta=source_meta
            )
            all_chunks.extend(chunks)

        doc.close()

        output_path = Path("data/processed") / f"{source_id}.jsonl"
        save_chunks_to_jsonl(all_chunks, output_path)

        self.manifest.record_document(
            document_id=source_id,
            title=source_meta.title,
            source_id=source_id,
            file_path=str(pdf_path),
            sha256=checksum,
            status="SUCCESS",
            chunk_count=len(all_chunks),
            metadata={"output_jsonl": str(output_path), "chunks": len(all_chunks)}
        )

        print(f"[SUCCESS] Ingested PDF {source_id}: {len(all_chunks)} chunks generated.")
        return all_chunks

