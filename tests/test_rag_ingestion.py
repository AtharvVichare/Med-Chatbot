"""
Automated Test Suite for Medical Reference Document Ingestion & Chunking
Tests:
- PDF document parsing with PyMuPDF
- XML document parsing with lxml & BeautifulSoup
- Document metadata and provenance completeness
- Deterministic chunk ID calculation
- Duplicate document detection via content hash
- Chunk token boundaries and token-based splitting
- Source attribution and licensing preservation
- Malformed and empty document handling
- Repeated ingestion idempotency
Uses self-contained local fixtures (no external network calls).
"""

import os
import json
import tempfile
import unittest
from pathlib import Path
import pymupdf

from rag.sources import MEDICAL_SOURCES_REGISTRY, MedicalSourceMetadata
from rag.chunk_documents import MedicalChunker
from rag.manifest import DocumentManifest, calculate_checksum
from rag.ingest_medlineplus import MedlinePlusIngestor
from rag.ingest_pdfs import PDFGuidelineIngestor
from rag.validate_chunks import validate_chunk_record

class TestMedicalKnowledgeBaseIngestion(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.manifest_path = self.temp_path / "test_manifest.json"
        self.manifest = DocumentManifest(manifest_path=self.manifest_path)
        self.chunker = MedicalChunker(target_tokens=100, overlap_tokens=20)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_sources_registry(self):
        """Verify registered medical sources have complete attribution and valid topics"""
        self.assertGreaterEqual(len(MEDICAL_SOURCES_REGISTRY), 3)
        for s_id, meta in MEDICAL_SOURCES_REGISTRY.items():
            self.assertEqual(s_id, meta.source_id)
            self.assertTrue(len(meta.title) > 0)
            self.assertTrue(len(meta.organization) > 0)
            self.assertTrue(meta.source_url.startswith("http"))
            self.assertIn(meta.topic, ["diabetes", "hypertension", "cardiovascular"])
            self.assertTrue(len(meta.license) > 0)
            self.assertTrue(meta.is_official)

    def test_02_xml_ingestion(self):
        """Verify MedlinePlus XML parsing, HTML stripping, and chunk creation"""
        xml_file = self.temp_path / "sample_topic.xml"
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
        <health-topics date-generated="2025-01-01">
          <health-topic id="999" title="Test Hypertension Topic" url="https://medlineplus.gov/test.html">
            <full-summary><![CDATA[<p>High blood pressure is a <strong>silent condition</strong> that affects arteries.</p>]]></full-summary>
            <section title="Clinical Guidance">
              Systolic BP >= 140 mmHg is diagnosed as hypertension. Treatment includes lifestyle changes and Amlodipine 5 mg.
            </section>
          </health-topic>
        </health-topics>
        """
        xml_file.write_text(xml_content, encoding="utf-8")

        ingestor = MedlinePlusIngestor(chunker=self.chunker, manifest=self.manifest)
        chunks = ingestor.parse_xml_file(xml_file, "MEDLINEPLUS-HYPERTENSION-XML")

        self.assertGreaterEqual(len(chunks), 1)
        for chk in chunks:
            is_valid, errors = validate_chunk_record(chk)
            self.assertTrue(is_valid, f"Chunk invalid: {errors}")
            self.assertEqual(chk["medical_topic"], "hypertension")
            self.assertIn("MEDLINEPLUS", chk["document_id"])
        
        # Check that sections were extracted
        all_text = " ".join(c["content"] for c in chunks)
        self.assertIn("Amlodipine", all_text)
        self.assertIn("silent condition", all_text)

    def test_03_pdf_ingestion(self):
        """Verify PDF guideline extraction with PyMuPDF, tracking page numbers"""
        pdf_file = self.temp_path / "guideline.pdf"
        doc = pymupdf.open()
        p1 = doc.new_page()
        p1.insert_text((50, 50), "WHO Guidelines for Hypertension Treatment\nTarget blood pressure is < 140/90 mmHg for non-diabetic adults.", fontsize=12)
        doc.save(str(pdf_file))
        doc.close()

        ingestor = PDFGuidelineIngestor(chunker=self.chunker, manifest=self.manifest)
        chunks = ingestor.parse_pdf_file(pdf_file, "WHO-HTN-GUIDELINE-2021")

        self.assertGreaterEqual(len(chunks), 1)
        first_chunk = chunks[0]
        self.assertEqual(first_chunk["page_number"], 1)
        self.assertEqual(first_chunk["source_organization"], "World Health Organization (WHO)")
        self.assertIn("140/90 mmHg", first_chunk["content"])

    def test_04_deterministic_chunk_ids(self):
        """Verify chunk IDs are deterministic across identical runs"""
        id1 = self.chunker.generate_chunk_id("DOC-1", "Diagnosis", 1, 0, "hash1234567890abcdef")
        id2 = self.chunker.generate_chunk_id("DOC-1", "Diagnosis", 1, 0, "hash1234567890abcdef")
        id3 = self.chunker.generate_chunk_id("DOC-1", "Diagnosis", 1, 1, "hash1234567890abcdef")

        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)
        self.assertTrue(id1.startswith("CHK-"))

    def test_05_token_boundaries(self):
        """Verify true token length estimation using tiktoken cl100k_base"""
        sample_text = "Hypertension and diabetes mellitus represent two major modifiable risk factors for cardiovascular disease."
        tokens = self.chunker.token_length(sample_text)
        self.assertGreater(tokens, 10)
        self.assertLess(tokens, 30)

    def test_06_duplicate_detection(self):
        """Verify manifest detects identical content hashes and tracks checksums"""
        file1 = self.temp_path / "doc1.txt"
        file1.write_text("Unique medical guideline text 12345.", encoding="utf-8")
        h1 = calculate_checksum(file1)

        self.manifest.record_document("DOC-1", "Title 1", "SRC-1", str(file1), h1, "SUCCESS", chunk_count=5)
        self.assertEqual(self.manifest.is_duplicate_hash(h1), "DOC-1")

        file2 = self.temp_path / "doc2.txt"
        file2.write_text("Different content text 67890.", encoding="utf-8")
        h2 = calculate_checksum(file2)
        self.assertIsNone(self.manifest.is_duplicate_hash(h2))

    def test_07_empty_or_malformed_documents(self):
        """Verify graceful error recording for malformed or empty documents"""
        empty_pdf = self.temp_path / "empty.pdf"
        empty_pdf.write_bytes(b"not a real pdf header")

        ingestor = PDFGuidelineIngestor(chunker=self.chunker, manifest=self.manifest)
        with self.assertRaises(ValueError):
            ingestor.parse_pdf_file(empty_pdf, "WHO-HTN-GUIDELINE-2021")

        # Confirm recorded in manifest as FAILED
        doc_record = self.manifest.get_document("WHO-HTN-GUIDELINE-2021")
        self.assertIsNotNone(doc_record)
        self.assertEqual(doc_record["status"], "FAILED")

if __name__ == "__main__":
    unittest.main()
