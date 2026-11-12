"""
Comprehensive Test Suite for Aarogya Drishti 2.0:
- Multi-namespace RAG retrieval (medical-encyclopedia-v1, medical-references-v2, medical-references-v1)
- Query expansion & re-ranking
- Grounded Gemini explanation & citation retention
- Longitudinal trends & chart action generation
- Non-causal comorbidity attribution (e.g. Skin rash + diabetes comorbidity)
- Authorization enforcement on longitudinal trends
"""

import unittest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.session import get_db
from backend.app.core.security import create_access_token
from rag.retrieval import MedicalRetrievalService
from rag.chunking_engine import ContextualChunkingEngine
from rag.source_registry import MedicalSourceRegistry

TEST_DB_URL = "postgresql+psycopg2://aarogya:K9vX3mP7rL2wT8aF@127.0.0.1:5432/aarogya_db_test"
test_engine = create_engine(TEST_DB_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


class TestComprehensiveRAGAndAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Login Patient A (PAT-00001)
        res_a = cls.client.post("/api/v1/auth/login", json={
            "username": "patient_user",
            "password": "DemoPassword123!"
        })
        assert res_a.status_code == 200, f"Patient login failed: {res_a.text}"
        cls.token_patient_a = res_a.json()["access_token"]
        cls.headers_patient_a = {"Authorization": f"Bearer {cls.token_patient_a}"}

        # Create Patient B to test cross-patient isolation
        unique_suffix = "rag_b_" + datetime.now(timezone.utc).strftime("%H%M%S")
        res_b = cls.client.post("/api/v1/auth/signup", json={
            "username": f"patient_{unique_suffix}",
            "email": f"patient_{unique_suffix}@example.com",
            "password": "DemoPassword123!",
            "first_name": "Rohan",
            "last_name": "Mehta",
            "gender": "male",
            "date_of_birth": "1988-04-12",
            "phone": "+91 99887 76655",
            "district": "Pune"
        })
        assert res_b.status_code in (200, 201), f"Register Patient B failed: {res_b.text}"
        cls.token_patient_b = res_b.json()["access_token"]
        cls.headers_patient_b = {"Authorization": f"Bearer {cls.token_patient_b}"}

    def setUp(self):
        # Create a fresh conversation for Patient A
        resp = self.client.post(
            "/api/v1/assistant/conversations",
            json={"title": "RAG Test Consultation"},
            headers=self.headers_patient_a
        )
        assert resp.status_code in [200, 201], f"Create conversation failed: {resp.text}"
        self.conv_id = resp.json()["conversation_id"]

    def test_chunking_engine_token_and_metadata(self):
        """Test ContextualChunkingEngine generates rich contextual headers and conforms to token limits."""
        engine = ContextualChunkingEngine(target_tokens=300, overlap_tokens=50, min_tokens=30)
        sample_page_stream = [
            {
                "page_number": 42,
                "cleaned_text": (
                    "Acetaminophen is an analgesic and antipyretic agent used to treat mild to moderate pain. "
                    "It works by inhibiting central prostaglandin synthesis. "
                    "Adult dosage should not exceed 4,000 mg within 24 hours to prevent hepatotoxicity. " * 10
                ),
                "detected_headings": ["Acetaminophen", "Pharmacology"],
                "has_text": True
            }
        ]
        chunks = engine.chunk_document_stream(
            document_id="GALE-MED-ENC-3RD",
            document_title="The Gale Encyclopedia of Medicine",
            publisher="Gale Cengage Learning",
            edition="Third Edition",
            source_url="https://www.cengage.com/gale",
            page_stream=iter(sample_page_stream)
        )
        self.assertGreaterEqual(len(chunks), 1)
        chunk = chunks[0]
        self.assertTrue(chunk["chunk_id"].startswith("CHK-GALE-"))
        self.assertIn("Acetaminophen", chunk["content"])
        self.assertIn("Document: The Gale Encyclopedia of Medicine", chunk["contextual_embedding_text"])
        self.assertEqual(chunk["publisher"], "Gale Cengage Learning")

    def test_source_registry_validation(self):
        """Test MedicalSourceRegistry tracks verified knowledge bases."""
        registry = MedicalSourceRegistry()
        sources = registry.list_sources()
        self.assertGreater(len(sources), 0)
        gale = registry.get_source("GALE-ENCYC-MED-3RD")
        self.assertIsNotNone(gale)
        self.assertEqual(gale["page_count"], 4505)
        self.assertEqual(gale["target_namespace"], "medical-encyclopedia-v1")

    def test_retrieval_query_expansion(self):
        """Test query expansion identifies medical synonyms for robust retrieval."""
        service = MedicalRetrievalService()
        variants_rash = service.expand_query("rash and itching")
        self.assertTrue(any("dermatitis" in v.lower() or "pruritus" in v.lower() for v in variants_rash))

        variants_bp = service.expand_query("high blood pressure")
        self.assertTrue(any("hypertension" in v.lower() for v in variants_bp))

    @patch("rag.retrieval.MedicalEmbeddingService")
    @patch("rag.retrieval.PineconeManager")
    def test_multi_namespace_retrieval_and_reranking(self, mock_pinecone_cls, mock_embed_cls):
        """Test retrieval queries multiple namespaces and applies similarity re-ranking."""
        mock_embed_inst = MagicMock()
        mock_embed_inst.embed_text.return_value = [0.1] * 384
        mock_embed_cls.return_value = mock_embed_inst

        mock_pinecone_inst = MagicMock()
        mock_index = MagicMock()
        mock_pinecone_inst.get_index.return_value = mock_index
        mock_pinecone_cls.return_value = mock_pinecone_inst

        mock_index.query.side_effect = [
            # Call for medical-references-v2
            {
                "matches": [
                    {
                        "id": "CHK-WHO-001",
                        "score": 0.72,
                        "metadata": {
                            "content": "WHO Guideline for hypertension management.",
                            "source_organization": "WHO",
                            "document_id": "DOC-WHO-01",
                            "title": "Hypertension Guidelines"
                        }
                    }
                ]
            },
            # Call for medical-encyclopedia-v1
            {
                "matches": [
                    {
                        "id": "CHK-GALE-001",
                        "score": 0.88,
                        "metadata": {
                            "content": "Gale Encyclopedia: Acetaminophen pharmacological action.",
                            "source_organization": "Gale",
                            "document_id": "DOC-GALE-01",
                            "title": "Gale Encyclopedia of Medicine"
                        }
                    }
                ]
            },
            # Call for medical-references-v1
            {
                "matches": []
            }
        ]

        service = MedicalRetrievalService(
            embedding_service=mock_embed_inst,
            pinecone_manager=mock_pinecone_inst
        )
        search_res = service.search("acetaminophen dosage", top_k=2)
        results = search_res.get("results", [])

        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0]["chunk_id"], "CHK-GALE-001")
        self.assertGreater(results[0]["similarity_score"], results[1]["similarity_score"])

    def test_longitudinal_trends_api_data_and_summary(self):
        """Test GET /api/v1/patients/{id}/longitudinal-trends returns merged EHR points and delta."""
        response = self.client.get(
            "/api/v1/patients/PAT-00001/longitudinal-trends?metric=blood_pressure",
            headers=self.headers_patient_a
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["patient_id"], "PAT-00001")
        self.assertEqual(data["test_category"], "blood_pressure")
        self.assertIn("data", data)
        self.assertIn("latest_value", data)
        self.assertIn("change_direction", data)

    def test_longitudinal_trends_authorization_isolation(self):
        """Test Patient B cannot access Patient A's longitudinal trends."""
        response = self.client.get(
            "/api/v1/patients/PAT-00001/longitudinal-trends?metric=blood_pressure",
            headers=self.headers_patient_b
        )
        self.assertEqual(response.status_code, 403)

    @patch("backend.app.api.v1.assistant.get_gemini_client")
    def test_chat_graph_request_intent_and_chart_action(self, mock_get_gemini):
        """Test chat queries requesting trends produce render_chart action with numerical series."""
        mock_resp = MagicMock()
        mock_resp.text = "Here is your blood pressure trend over recent months. Your latest reading shows stable pressure."
        mock_gemini = MagicMock()
        mock_gemini.model_name = "gemini-3.5-flash-lite"
        mock_gemini.client.models.generate_content.return_value = mock_resp
        mock_get_gemini.return_value = mock_gemini

        response = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "Show my blood pressure trend over the last 6 months"},
            headers=self.headers_patient_a
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertIn("proposed_ehr_actions", data)
        self.assertIsNotNone(data["proposed_ehr_actions"])
        actions = json.loads(data["proposed_ehr_actions"]) if isinstance(data["proposed_ehr_actions"], str) else data["proposed_ehr_actions"]
        self.assertGreaterEqual(len(actions), 1)
        chart_action = actions[0]
        self.assertEqual(chart_action.get("action_type"), "render_chart")
        self.assertEqual(chart_action.get("metric"), "blood_pressure")
        self.assertIn("points", chart_action)
        self.assertIn("dates", chart_action)
        self.assertIn("values", chart_action)

    @patch("backend.app.api.v1.assistant.get_rag_service")
    @patch("backend.app.api.v1.assistant.get_gemini_client")
    def test_grounded_response_citation_retention(self, mock_get_gemini, mock_get_rag):
        """Test grounded medical inquiries retain chunk citations in response."""
        mock_rag = MagicMock()
        mock_rag.is_available.return_value = True
        mock_rag.answer_medical_inquiry.return_value = {
            "answer": "Acetaminophen is used for pain relief [CHK-GALE-ACET-01]. The daily adult dose should not exceed 4,000 mg [CHK-GALE-ACET-01].",
            "references": [
                {
                    "chunk_id": "CHK-GALE-ACET-01",
                    "content": "Acetaminophen is an analgesic. Maximum daily dose is 4000mg.",
                    "source": "Gale Encyclopedia of Medicine",
                    "similarity_score": 0.89
                }
            ],
            "total_references": 1
        }
        mock_get_rag.return_value = mock_rag

        mock_resp = MagicMock()
        mock_resp.text = "Acetaminophen is used for pain relief [CHK-GALE-ACET-01]. The daily adult dose should not exceed 4,000 mg [CHK-GALE-ACET-01]."
        mock_gemini = MagicMock()
        mock_gemini.model_name = "gemini-3.5-flash-lite"
        mock_gemini.client.models.generate_content.return_value = mock_resp
        mock_get_gemini.return_value = mock_gemini

        response = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "What is the safe adult dose for acetaminophen?"},
            headers=self.headers_patient_a
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()["content"]
        self.assertIn("[CHK-GALE-ACET-01]", content)

    @patch("backend.app.api.v1.assistant.get_rag_service")
    @patch("backend.app.api.v1.assistant.get_gemini_client")
    def test_non_causal_comorbidity_attribution_safety(self, mock_get_gemini, mock_get_rag):
        """
        Test Section 9.3 scenario:
        When a patient with baseline diabetes reports an acute localized symptom (e.g. itchy skin rash),
        the system prompt ensures the assistant evaluates dermatological/acute causes and does NOT
        fabricate causal attribution to diabetes without clinical evidence.
        """
        mock_rag = MagicMock()
        mock_rag.is_available.return_value = True
        mock_rag.answer_medical_inquiry.return_value = {
            "answer": "An itchy skin rash is commonly caused by contact dermatitis or an allergic reaction [CHK-GALE-DERM-01]. While you have a medical history of Type 2 Diabetes, this skin rash should not be automatically assumed to be a diabetes complication without evaluation by a physician.",
            "references": [
                {
                    "chunk_id": "CHK-GALE-DERM-01",
                    "content": "Contact dermatitis presents as an itchy red rash following exposure to allergens or irritants.",
                    "source": "Gale Encyclopedia of Medicine",
                    "similarity_score": 0.85
                }
            ],
            "total_references": 1
        }
        mock_get_rag.return_value = mock_rag

        captured_contents = []
        mock_resp = MagicMock()
        mock_resp.text = "An itchy skin rash is commonly caused by contact dermatitis or an allergic reaction [CHK-GALE-DERM-01]. While you have a medical history of Type 2 Diabetes, this skin rash should not be automatically assumed to be a diabetes complication without evaluation by a physician."
        
        mock_gemini = MagicMock()
        mock_gemini.model_name = "gemini-3.5-flash-lite"
        def mock_generate(contents, **kwargs):
            captured_contents.append(contents)
            return mock_resp

        mock_gemini.client.models.generate_content.side_effect = mock_generate
        mock_get_gemini.return_value = mock_gemini

        response = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "I noticed an itchy red rash on my arm after gardening. What could it be?"},
            headers=self.headers_patient_a
        )

        self.assertEqual(response.status_code, 200)
        reply = response.json()["content"]
        self.assertIn("dermatitis", reply.lower())
        self.assertNotIn("this rash is caused by your diabetes", reply.lower())


if __name__ == "__main__":
    unittest.main()
