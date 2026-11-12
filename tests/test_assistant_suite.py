"""
Regression and Integration Test Suite for Aarogya Drishti 2.0 AI Health Assistant.
Tests all 15 scenarios specified in Section 9:
1. Greeting: "Hi"
2. Greeting: "Hello"
3. Acknowledgement: "Okay"
4. Gratitude: "Thank you"
5. General medical question: "What is diabetes?"
6. Symptom-related question: "I have a persistent cough"
7. Patient EHR question: "What was my last BP?"
8. Medical PDF/lab report question: "Explain my HbA1c report"
9. Gemini unavailable (mocked)
10. Gemini rate limited / 429 (mocked retry)
11. Pinecone unavailable (mocked graceful fallback)
12. Empty Gemini response (mocked fallback)
13. Invalid API response handling
14. Conversation history retrieval (GET /conversations/{id}/messages)
15. Unauthorized conversation access (Patient B accessing Patient A's conversation)
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import timedelta, datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.session import get_db
from backend.app.core.security import create_access_token
from backend.app.db.models import ChatConversation, ChatMessage

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

class TestAIAssistantSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        
        # Patient A (Isha Nair, PAT-00001) using synthetic demo credentials
        res_a = cls.client.post("/api/v1/auth/login", json={
            "username": "patient_user",
            "password": "DemoPassword123!"
        })
        cls.token_patient_a = res_a.json()["access_token"]
        cls.headers_patient_a = {"Authorization": f"Bearer {cls.token_patient_a}"}

        # Patient B dynamically created
        unique_suffix = "b_" + datetime.now(timezone.utc).strftime("%H%M%S")
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
        cls.token_patient_b = res_b.json()["access_token"]
        cls.headers_patient_b = {"Authorization": f"Bearer {cls.token_patient_b}"}

    def setUp(self):
        # Create a fresh conversation for Patient A
        resp = self.client.post(
            "/api/v1/assistant/conversations",
            json={"title": "Test Consultation"},
            headers=self.headers_patient_a
        )
        self.assertIn(resp.status_code, [200, 201])
        self.conv_id = resp.json()["conversation_id"]

    # Scenario 1: Greeting "Hi"
    def test_01_greeting_hi(self):
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "Hi"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertIn("Hello", data["content"])
        self.assertNotIn("While processing clinical reference guidelines", data["content"])

    # Scenario 2: Greeting "Hello"
    def test_02_greeting_hello(self):
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "Hello there!"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertIn("Hello", data["content"])
        self.assertNotIn("While processing clinical reference guidelines", data["content"])

    # Scenario 3: Acknowledgement "Okay"
    def test_03_acknowledgement_okay(self):
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "Okay"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertTrue(any(word in data["content"].lower() for word in ["help", "assist", "understood", "questions", "here"]))
        self.assertNotIn("While processing clinical reference guidelines", data["content"])

    # Scenario 4: Gratitude "Thank you"
    def test_04_gratitude_thank_you(self):
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "Thank you very much!"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertTrue(any(word in data["content"].lower() for word in ["welcome", "pleasure", "glad", "anytime"]))
        self.assertNotIn("While processing clinical reference guidelines", data["content"])

    # Scenario 5: General medical question "What is diabetes?"
    def test_05_general_medical_question(self):
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "What is diabetes and what are common signs?"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertTrue(len(data["content"]) > 50)
        self.assertTrue("diabetes" in data["content"].lower() or "glucose" in data["content"].lower() or "blood sugar" in data["content"].lower())
        self.assertNotIn("While processing clinical reference guidelines, please note", data["content"])

    # Scenario 6: Symptom-related question "I have a persistent cough"
    def test_06_symptom_question(self):
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "I have had a persistent cough and mild chest tightness for three days"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertTrue(len(data["content"]) > 50)
        self.assertNotIn("While processing clinical reference guidelines, please note", data["content"])

    # Scenario 7: Patient EHR question "What was my last BP?"
    def test_07_patient_ehr_question(self):
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "What was my last BP and what medications am I currently taking?"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        # PAT-00001 has blood pressure observations or active medications in EHR
        self.assertTrue("record" in data["content"].lower() or "blood pressure" in data["content"].lower() or "medication" in data["content"].lower() or "active" in data["content"].lower())
        self.assertNotIn("While processing clinical reference guidelines", data["content"])

    # Scenario 8: Medical PDF/lab report question "Explain my HbA1c report"
    def test_08_lab_report_question(self):
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "Can you explain what my HbA1c lab test means in my records?"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertTrue("hba1c" in data["content"].lower() or "hemoglobin" in data["content"].lower() or "glucose" in data["content"].lower() or "record" in data["content"].lower())
        self.assertNotIn("While processing clinical reference guidelines", data["content"])

    # Scenario 9: Gemini unavailable (mocked)
    @patch("backend.app.api.v1.assistant.get_gemini_client")
    @patch("backend.app.api.v1.assistant.get_rag_service")
    def test_09_gemini_unavailable(self, mock_get_rag, mock_get_gemini):
        # Simulate RAG failing and Gemini failing as well
        mock_get_rag.return_value.answer_medical_inquiry.side_effect = Exception("RAG service unavailable")
        mock_gemini = MagicMock()
        mock_gemini.client.models.generate_content.side_effect = Exception("ServiceUnavailable: 503 Backend service down")
        mock_gemini.model_name = "gemini-3.5-flash-lite"
        mock_get_gemini.return_value = mock_gemini

        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "What is the recommended treatment for seasonal allergies?"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertIn("temporarily unavailable", data["content"].lower())
        self.assertNotIn("traceback", data["content"].lower())

    # Scenario 10: Gemini rate limited / 429 (mocked retry)
    @patch("backend.app.api.v1.assistant.get_gemini_client")
    def test_10_gemini_rate_limited(self, mock_get_gemini):
        mock_success = MagicMock()
        mock_success.text = "Allergies can be managed with antihistamines and avoidance of allergens."
        mock_gemini = MagicMock()
        mock_gemini.model_name = "gemini-3.5-flash-lite"
        mock_gemini.client.models.generate_content.side_effect = [
            Exception("ResourceExhausted: 429 Quota exceeded"),
            mock_success
        ]
        mock_get_gemini.return_value = mock_gemini

        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "What are common treatments for allergies?"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertTrue(len(data["content"]) > 10)

    # Scenario 11: Pinecone unavailable (mocked graceful fallback)
    @patch("backend.app.api.v1.assistant.get_rag_service")
    def test_11_pinecone_unavailable_graceful_fallback(self, mock_get_rag):
        mock_get_rag.return_value.answer_medical_inquiry.side_effect = Exception("PineconeConnectionError: Failed to connect to Pinecone vector DB")
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "What is the standard dosage guidelines for metformin?"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertTrue(len(data["content"]) > 20)
        self.assertNotIn("While processing clinical reference guidelines, please note", data["content"])

    # Scenario 12: Empty Gemini response (mocked fallback)
    @patch("backend.app.api.v1.assistant.get_gemini_client")
    def test_12_empty_gemini_response(self, mock_get_gemini):
        mock_empty = MagicMock()
        mock_empty.text = "   "
        mock_gemini = MagicMock()
        mock_gemini.model_name = "gemini-3.5-flash-lite"
        mock_gemini.client.models.generate_content.return_value = mock_empty
        mock_get_gemini.return_value = mock_gemini

        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "Can you explain asthma symptoms?"},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sender"], "assistant")
        self.assertTrue(len(data["content"]) > 10)
        self.assertNotIn("While processing clinical reference guidelines, please note", data["content"])

    # Scenario 13: Invalid API request handling
    def test_13_invalid_request_handling(self):
        # Empty string message
        resp = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "    "},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 400)

        # Missing content field
        resp2 = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={},
            headers=self.headers_patient_a
        )
        self.assertEqual(resp2.status_code, 422)

    # Scenario 14: Conversation history retrieval (GET /conversations/{id}/messages)
    def test_14_conversation_history_retrieval(self):
        # Send a message first
        self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "Hi Aarogya assistant"},
            headers=self.headers_patient_a
        )
        resp = self.client.get(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            headers=self.headers_patient_a
        )
        self.assertEqual(resp.status_code, 200)
        msgs = resp.json()
        self.assertIsInstance(msgs, list)
        self.assertGreaterEqual(len(msgs), 2)
        # Verify ISO UTC timezone format on timestamps
        first_msg = msgs[0]
        self.assertIn("created_at", first_msg)
        self.assertTrue(first_msg["created_at"].endswith("+00:00") or first_msg["created_at"].endswith("Z"))

    # Scenario 15: Unauthorized conversation access (Patient B accessing Patient A's conversation)
    def test_15_unauthorized_conversation_access(self):
        # Patient B tries to get Patient A's conversation messages
        resp = self.client.get(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            headers=self.headers_patient_b
        )
        self.assertEqual(resp.status_code, 403)

        # Patient B tries to send a message to Patient A's conversation
        resp2 = self.client.post(
            f"/api/v1/assistant/conversations/{self.conv_id}/messages",
            json={"content": "Attempting unauthorized injection"},
            headers=self.headers_patient_b
        )
        self.assertEqual(resp2.status_code, 403)


if __name__ == "__main__":
    unittest.main()
