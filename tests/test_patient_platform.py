"""
Integration & Regression Tests for Aarogya Drishti 2.0 Patient Platform Transformation
Tests all 7 Transformation Milestones:
1. Dynamic User Signup & Profile Me endpoint
2. Patient-Controlled EHR updates (Conditions, Medications, Discontinuation)
3. Allergies CRUD (with 204 verification)
4. Family Health History & Pedigree with hereditary conditions
5. Daily Health Tracking & Measurements
6. Medical Document Ingestion & Observation Confirmation
7. AI Health Assistant Conversations & Action Confirmation
8. Prospective 12-Month Incident Diabetes Risk Model
"""

import os
import io
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.session import get_db
from backend.app.db.models import Base

TEST_DB_URL = "postgresql+psycopg2://aarogya:K9vX3mP7rL2wT8aF@127.0.0.1:5432/aarogya_db_test"
test_engine = create_engine(TEST_DB_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Ensure tables exist in test db
Base.metadata.create_all(bind=test_engine)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


class TestPatientPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = TestSessionLocal()

        # Doctor login token for provider operations
        res_doc = cls.client.post("/api/v1/auth/login", json={
            "username": "doctor_user",
            "password": "DemoPassword123!"
        })
        cls.doc_token = res_doc.json()["access_token"]
        cls.doc_headers = {"Authorization": f"Bearer {cls.doc_token}"}

        # Patient demo login token (Isha Nair PAT-00001)
        res_pat = cls.client.post("/api/v1/auth/login", json={
            "username": "patient_user",
            "password": "DemoPassword123!"
        })
        cls.pat_token = res_pat.json()["access_token"]
        cls.pat_headers = {"Authorization": f"Bearer {cls.pat_token}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        test_engine.dispose()

    # --- 1. Dynamic User Signup & Auth ---
    def test_01_user_signup_and_profile(self):
        unique_suffix = os.urandom(3).hex()
        signup_data = {
            "username": f"patient_{unique_suffix}",
            "email": f"patient_{unique_suffix}@example.com",
            "password": "SecurePassword123!",
            "first_name": "Ananya",
            "last_name": "Desai",
            "gender": "female",
            "date_of_birth": "1992-08-20",
            "phone": "+91 98111 22233",
            "district": "Pune"
        }

        res = self.client.post("/api/v1/auth/signup", json=signup_data)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "patient")
        self.assertTrue(data["patient_id"].startswith("PAT-"))

        # Verify /auth/me with newly created token
        new_headers = {"Authorization": f"Bearer {data['access_token']}"}
        res_me = self.client.get("/api/v1/auth/me", headers=new_headers)
        self.assertEqual(res_me.status_code, 200)
        me_data = res_me.json()
        self.assertEqual(me_data["full_name"], "Ananya Desai")
        self.assertEqual(me_data["patient_id"], data["patient_id"])

    def test_02_forgot_password(self):
        res = self.client.post("/api/v1/auth/forgot-password", json={"email": "isha.nair@example.com"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("password reset", res.json()["message"].lower())

    # --- 2. Patient Profile & EHR Updates ---
    def test_03_patient_profile_update(self):
        res = self.client.patch("/api/v1/patients/PAT-00001", json={
            "phone_number": "+91 98200 99999",
            "district": "Mumbai Suburban"
        }, headers=self.pat_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["phone_number"], "+91 98200 99999")
        self.assertEqual(data["district"], "Mumbai Suburban")

    def test_04_add_condition_and_medication(self):
        # Add condition
        res_cond = self.client.post("/api/v1/patients/PAT-00001/conditions", json={
            "condition_code": "I10",
            "condition_name": "Essential Hypertension",
            "onset_date": "2024-01-15",
            "category": "cardiovascular"
        }, headers=self.pat_headers)
        self.assertEqual(res_cond.status_code, 201)
        cond_data = res_cond.json()
        self.assertEqual(cond_data["diagnosis_code"], "I10")

        # Add medication
        res_med = self.client.post("/api/v1/patients/PAT-00001/medications", json={
            "medication_name": "Amlodipine",
            "dosage": "5mg",
            "frequency": "Once daily morning",
            "prescribing_doctor": "Dr. Arvind Patel"
        }, headers=self.pat_headers)
        self.assertEqual(res_med.status_code, 201)
        med_data = res_med.json()
        med_id = med_data["medication_id"]

        # Discontinue medication
        res_disc = self.client.patch(f"/api/v1/patients/PAT-00001/medications/{med_id}/discontinue", headers=self.pat_headers)
        self.assertEqual(res_disc.status_code, 200)

    # --- 3. Allergies CRUD ---
    def test_05_allergies_lifecycle(self):
        # Create allergy
        res_create = self.client.post("/api/v1/patients/PAT-00001/allergies", json={
            "substance": "Penicillin",
            "reaction": "Urticaria and facial swelling",
            "severity": "severe",
            "category": "medication"
        }, headers=self.pat_headers)
        self.assertEqual(res_create.status_code, 201)
        allergy_id = res_create.json()["allergy_id"]

        # List allergies
        res_list = self.client.get("/api/v1/patients/PAT-00001/allergies", headers=self.pat_headers)
        self.assertEqual(res_list.status_code, 200)
        self.assertTrue(any(a["allergy_id"] == allergy_id for a in res_list.json()))

        # Delete allergy
        res_del = self.client.delete(f"/api/v1/patients/PAT-00001/allergies/{allergy_id}", headers=self.pat_headers)
        self.assertIn(res_del.status_code, [200, 204])

    # --- 4. Family Health History CRUD ---
    def test_06_family_history_lifecycle(self):
        # Add relative with conditions
        res_create = self.client.post("/api/v1/patients/PAT-00001/family-history", json={
            "relative_name": "Ramesh Nair",
            "relation_type": "father",
            "is_deceased": False,
            "conditions": [
                {"condition_name": "Type 2 Diabetes", "approximate_age_at_onset": 52},
                {"condition_name": "Hypertension", "approximate_age_at_onset": 48}
            ]
        }, headers=self.pat_headers)
        self.assertEqual(res_create.status_code, 201)
        member_id = res_create.json()["id"]

        # Get family history
        res_get = self.client.get("/api/v1/patients/PAT-00001/family-history", headers=self.pat_headers)
        self.assertEqual(res_get.status_code, 200)
        members = res_get.json()
        self.assertTrue(any(m["id"] == member_id for m in members))

        # Delete member
        res_del = self.client.delete(f"/api/v1/patients/PAT-00001/family-history/{member_id}", headers=self.pat_headers)
        self.assertIn(res_del.status_code, [200, 204])

    # --- 5. Daily Health Tracking ---
    def test_07_daily_health_tracking(self):
        res_log = self.client.post("/api/v1/patients/PAT-00001/daily-tracking", json={
            "systolic_bp": 124,
            "diastolic_bp": 82,
            "pulse": 72,
            "fasting_glucose": 102.5,
            "spo2": 99,
            "sleep_hours": 7.5,
            "source": "wearable_test"
        }, headers=self.pat_headers)
        self.assertEqual(res_log.status_code, 201)

        # Get tracking logs
        res_get = self.client.get("/api/v1/patients/PAT-00001/daily-tracking?limit=10", headers=self.pat_headers)
        self.assertEqual(res_get.status_code, 200)
        logs = res_get.json()
        self.assertGreater(len(logs), 0)
        self.assertEqual(logs[0]["systolic_bp"], 124)

    # --- 6. Document Ingestion & Observation Extraction ---
    def test_08_document_upload_and_confirmation(self):
        # Create dummy lab report text file
        file_content = b"LABORATORY DIAGNOSTIC REPORT\nFasting Blood Sugar: 114 mg/dL\nHbA1c: 6.1 %\nBlood Pressure: 130/85 mmHg"
        files = {
            "file": ("lab_report_test.txt", io.BytesIO(file_content), "text/plain")
        }
        data = {
            "patient_id": "PAT-00001",
            "document_type": "lab_report"
        }

        res_upload = self.client.post("/api/v1/documents/upload", data=data, files=files, headers=self.pat_headers)
        self.assertEqual(res_upload.status_code, 201)
        doc = res_upload.json()
        self.assertEqual(doc["file_name"], "lab_report_test.txt")
        doc_id = doc["document_id"]

        # Confirm document observations into EHR
        res_confirm = self.client.post(f"/api/v1/documents/{doc_id}/confirm", headers=self.pat_headers)
        self.assertEqual(res_confirm.status_code, 200)
        self.assertEqual(res_confirm.json()["confirmation_status"], "confirmed")

    # --- 7. AI Health Assistant & Clinical Actions ---
    def test_09_assistant_conversation_and_action(self):
        # Create conversation
        res_conv = self.client.post("/api/v1/assistant/conversations", json={
            "title": "Hypertension & Diet Consultation"
        }, headers=self.pat_headers)
        self.assertEqual(res_conv.status_code, 201)
        conv_id = res_conv.json()["conversation_id"]

        # Post message
        res_msg = self.client.post(f"/api/v1/assistant/conversations/{conv_id}/messages", json={
            "content": "Can you advise on monitoring my blood pressure and fasting glucose?"
        }, headers=self.pat_headers)
        self.assertEqual(res_msg.status_code, 200)
        reply = res_msg.json()
        self.assertEqual(reply["sender"], "assistant")
        self.assertTrue(len(reply["content"]) > 10)

        # Confirm structured action
        action_payload = {
            "message_id": reply["message_id"],
            "action_type": "measurement",
            "data": {
                "name": "Blood Pressure Check",
                "systolic": 125,
                "diastolic": 82
            }
        }
        res_action = self.client.post("/api/v1/assistant/confirm-action", json=action_payload, headers=self.pat_headers)
        self.assertEqual(res_action.status_code, 200)
        self.assertEqual(res_action.json()["status"], "confirmed")

    # --- 8. Prospective 12-Month Incident Diabetes Risk ---
    def test_10_diabetes_future_risk_insight(self):
        res = self.client.get("/api/v1/insights/diabetes-risk/PAT-00001", headers=self.pat_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Diabetes", data["target_condition"])
        self.assertEqual(data["prediction_horizon"].lower(), "12 months")
        self.assertEqual(data["lookback_window"].lower(), "24 months")
        self.assertIn("contributing_factors", data)
        self.assertIn("clinical_disclaimer", data)
        self.assertIn("research", data["clinical_disclaimer"].lower())


if __name__ == "__main__":
    unittest.main()
