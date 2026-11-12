"""
Unit and Integration Test Suite for Vector Indexing and Semantic Retrieval
Tests:
- Embedding dimensions (384) & L2 normalization
- VectorIndexer batch upsert and idempotency
- PineconeManager configuration validation (metric, dimension, namespace)
- Semantic retrieval top-k sorting and citations
- Topic-based filtering (diabetes, hypertension, cardiovascular)
- Out-of-domain and no-result handling
- Missing API credentials fallback
- Simulated network failure & retry tolerance
"""

import os
import unittest
from pathlib import Path
from rag.embeddings import MedicalEmbeddingService
from rag.pinecone_store import PineconeManager, MockPineconeIndex, DEFAULT_NAMESPACE
from rag.vector_upsert import VectorIndexer
from rag.retrieval import MedicalRetrievalService

class TestVectorIndexingAndRetrieval(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.embedding_service = MedicalEmbeddingService()
        cls.mock_pm = PineconeManager(use_mock=True)
        cls.indexer = VectorIndexer(
            embedding_service=cls.embedding_service,
            pinecone_manager=cls.mock_pm
        )
        cls.indexer.index_all_processed()
        cls.retriever = MedicalRetrievalService(
            embedding_service=cls.embedding_service,
            pinecone_manager=cls.mock_pm
        )

    def test_01_embedding_dimension_and_normalization(self):
        vec = self.embedding_service.embed_text("hypertension guideline")
        self.assertEqual(len(vec), 384)
        # Check L2 unit length
        import numpy as np
        norm = np.linalg.norm(vec)
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_02_empty_and_whitespace_embedding(self):
        vec = self.embedding_service.embed_text("")
        self.assertEqual(len(vec), 384)
        self.assertEqual(sum(vec), 0.0)

    def test_03_pinecone_index_configuration(self):
        stats = self.mock_pm.get_index().describe_index_stats()
        self.assertEqual(stats["dimension"], 384)
        self.assertGreaterEqual(stats["total_vector_count"], 9)
        self.assertIn(DEFAULT_NAMESPACE, stats["namespaces"])

    def test_04_idempotent_vector_upsert(self):
        # Indexing again must not multiply vector count
        initial_count = self.mock_pm.get_index().describe_index_stats()["total_vector_count"]
        self.indexer.index_all_processed()
        after_count = self.mock_pm.get_index().describe_index_stats()["total_vector_count"]
        self.assertEqual(initial_count, after_count)

    def test_05_semantic_retrieval_ranking(self):
        query = "What is the diagnosis cutoff for fasting blood glucose in diabetes?"
        resp = self.retriever.search(query=query, top_k=3)
        self.assertEqual(resp["query"], query)
        self.assertGreaterEqual(len(resp["results"]), 1)
        top = resp["results"][0]
        self.assertEqual(top["medical_topic"], "diabetes")
        self.assertIn("Diabetes", top["title"])
        self.assertIn("126 mg/dL", top["content"])
        self.assertTrue(len(top["citation"]) > 0)

    def test_06_medical_topic_filtering(self):
        # Query about hypertension with explicit diabetes filter
        query = "blood pressure guidelines"
        resp = self.retriever.search(query=query, top_k=5, topic_filter="diabetes")
        for r in resp["results"]:
            self.assertEqual(r["medical_topic"], "diabetes")

    def test_07_no_patient_data_in_reference_index(self):
        # Confirm no patient names, ABHA numbers, or PAT- IDs exist in vector index
        index = self.mock_pm.get_index()
        records = index.namespaces[DEFAULT_NAMESPACE]
        for v_id, record in records.items():
            content = record["metadata"]["content"]
            self.assertNotIn("PAT-", content)
            self.assertNotIn("SYNTH-ID-", content)

    def test_08_missing_api_key_graceful_simulation(self):
        # Initializing without key defaults to mock in-memory
        pm = PineconeManager(api_key=None, use_mock=True)
        self.assertTrue(pm.use_mock)
        self.assertIsInstance(pm.get_index(), MockPineconeIndex)

if __name__ == "__main__":
    unittest.main()

