"""
XML Medical Document Ingestor (MedlinePlus Health Topics)
Parses MedlinePlus health-topic XML files using lxml and BeautifulSoup:
- Extracts health topics, section titles, paragraphs, and medical summaries
- Cleans and normalizes HTML/formatting entities
- Attaches full provenance metadata and outputs token-aware chunks
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from lxml import etree

from rag.sources import MEDICAL_SOURCES_REGISTRY, get_source_metadata
from rag.chunk_documents import MedicalChunker, save_chunks_to_jsonl
from rag.manifest import DocumentManifest, calculate_checksum

def clean_html_text(html_content: str) -> str:
    if not html_content:
        return ""
    # Use BeautifulSoup to strip HTML markup while preserving text
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ")
    # Text normalization
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

class MedlinePlusIngestor:

    def __init__(self, chunker: Optional[MedicalChunker] = None, manifest: Optional[DocumentManifest] = None):
        self.chunker = chunker or MedicalChunker()
        self.manifest = manifest or DocumentManifest()

    def parse_xml_file(self, xml_path: Path, source_id: str) -> List[Dict[str, Any]]:
        source_meta = get_source_metadata(source_id)
        if not xml_path.exists():
            raise FileNotFoundError(f"XML file not found at: {xml_path}")

        checksum = calculate_checksum(xml_path)
        existing_doc = self.manifest.is_duplicate_hash(checksum)
        if existing_doc and existing_doc == source_id:
            print(f"[SKIP] Document {source_id} already ingested with identical checksum.")

        try:
            # Parse XML safely with lxml
            parser = etree.XMLParser(recover=True, remove_blank_text=True)
            tree = etree.parse(str(xml_path), parser)
            root = tree.getroot()
        except Exception as e:
            self.manifest.record_document(
                document_id=source_id,
                title=source_meta.title,
                source_id=source_id,
                file_path=str(xml_path),
                sha256=checksum,
                status="FAILED",
                error_message=f"XML Parsing Error: {str(e)}"
            )
            raise ValueError(f"Failed to parse XML file: {str(e)}")

        all_chunks: List[Dict[str, Any]] = []

        # MedlinePlus XML typically contains <health-topic> nodes
        topics = root.findall(".//health-topic") or [root]

        for topic in topics:
            topic_title = topic.get("title") or source_meta.title
            full_summary_elem = topic.find("full-summary")
            
            if full_summary_elem is not None and full_summary_elem.text:
                cleaned_summary = clean_html_text(full_summary_elem.text)
                if cleaned_summary:
                    chunks = self.chunker.chunk_section(
                        document_id=source_id,
                        section_heading=f"{topic_title} - Overview & Summary",
                        text_content=cleaned_summary,
                        page_number=None,
                        source_meta=source_meta
                    )
                    all_chunks.extend(chunks)

            # Sub-sections if available
            for section in topic.findall(".//section"):
                sec_title = section.get("title") or "Clinical Guidance"
                sec_content = clean_html_text("".join(section.itertext()))
                if len(sec_content) > 30:
                    chunks = self.chunker.chunk_section(
                        document_id=source_id,
                        section_heading=f"{topic_title} - {sec_title}",
                        text_content=sec_content,
                        page_number=None,
                        source_meta=source_meta
                    )
                    all_chunks.extend(chunks)

        if not all_chunks:
            # Fallback for generic XML text
            raw_text = clean_html_text("".join(root.itertext()))
            if raw_text:
                all_chunks = self.chunker.chunk_section(
                    document_id=source_id,
                    section_heading=f"{source_meta.title} - Full Content",
                    text_content=raw_text,
                    page_number=None,
                    source_meta=source_meta
                )

        output_path = Path("data/processed") / f"{source_id}.jsonl"
        save_chunks_to_jsonl(all_chunks, output_path)

        self.manifest.record_document(
            document_id=source_id,
            title=source_meta.title,
            source_id=source_id,
            file_path=str(xml_path),
            sha256=checksum,
            status="SUCCESS",
            chunk_count=len(all_chunks),
            metadata={"output_jsonl": str(output_path), "chunks": len(all_chunks)}
        )

        print(f"[SUCCESS] Ingested MedlinePlus XML {source_id}: {len(all_chunks)} chunks generated.")
        return all_chunks

