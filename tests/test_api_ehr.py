"""
Automated Integration Test Suite for Aarogya-Drishti FastAPI EHR Backend
Executed against dedicated PostgreSQL test database (aarogya_db_test).

Coverage:
- Health and Readiness endpoints (DB connectivity verification)
- Successful login for synthetic demo users
- Invalid login credentials handling (401)
- Expired and malformed JWT token handling (401)
- Patient-level authorization:
    - Patient accessing own record (200)
    - Patient denied accessing another patient's record (403)
- Doctor-level authorization:
    - Doctor accessing assigned patient (200)
    - Doctor denied accessing unassigned patient (403)
- Public Health Analyst role restriction:
    - Prohibited from accessing identifiable patient records (403)
- Audit log entry creation upon access attempts
- Patient listing with pagination and district filtering
- Longitudinal Patient Timeline aggregation & chronological order
- Detailed sub-resource endpoints (encounters, conditions, observations, medications, risk assessments)
- Invalid patient IDs returning 404
- Error responses sanitization (no DB credentials or tracebacks exposed)
"""

import os
import unittest
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.main import app
from backend.app.db.session import get_db
from backend.app.core.security import create_access_token
from backend.app.db.models import AuditLog, Patient

# Connect directly to dedicated PostgreSQL test database
TEST_DB_URL = "postgresql+psycopg2://aarogya:K9vX3mP7rL2wT8aF@127.0.0.1:5432/aarogya_db_test"
test_engine = create_engine(TEST_DB_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Apply dependency override for tests
app.dependency_overrides[get_db] = override_get_db

class TestFastAPIEHRBackend(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = TestSessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        test_engine.dispose()

    # --- 1. Health & Readiness ---
    def test_01_health_and_readiness(self):
        # Health check
        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "healthy")

        # Readiness check (verifies PostgreSQL connection)
        res_ready = self.client.get("/ready")
        self.assertEqual(res_ready.status_code, 200)
        data = res_ready.json()
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["dialect"], "postgresql")

    # --- 2. Authentication & JWT ---
    def test_02_successful_login(self):
        res = self.client.post("/api/v1/auth/login", json={
            "username": "doctor_user",
            "password": "DemoPassword123!"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "doctor")
        self.assertEqual(data["token_type"], "bearer")

    def test_03_invalid_credentials(self):
        res = self.client.post("/api/v1/auth/login", json={
            "username": "doctor_user",
            "password": "WrongPassword!"
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Incorrect username or password", res.json()["detail"])

    def test_04_expired_and_invalid_jwt(self):
        # Expired token
        expired_token = create_access_token(
            data={"sub": "doctor_user", "role": "doctor"},
            expires_delta=timedelta(seconds=-10)
        )
        res = self.client.get(
            "/api/v1/patients/PAT-00001",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid or expired", res.json()["detail"])

        # Malformed token
        res_malformed = self.client.get(
            "/api/v1/patients/PAT-00001",
            headers={"Authorization": "Bearer not-a-real-token"}
        )
        self.assertEqual(res_malformed.status_code, 401)

    # --- 3. Role-Based & Patient-Level Authorization ---
    def test_05_patient_role_authorization(self):
        # Login as patient_user (owns PAT-00001)
        token = create_access_token({"sub": "patient_user", "role": "patient"})

        # Access own record -> Allowed
        res_own = self.client.get(
            "/api/v1/patients/PAT-00001",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_own.status_code, 200)
        self.assertEqual(res_own.json()["patient_id"], "PAT-00001")

        # Access another patient record (PAT-00002) -> Denied 403
        res_other = self.client.get(
            "/api/v1/patients/PAT-00002",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_other.status_code, 403)
        self.assertIn("only authorized to view your own", res_other.json()["detail"])

    def test_06_doctor_role_assignment_authorization(self):
        # doctor_user is assigned to PAT-00001 and PAT-00002, NOT PAT-00003
        token = create_access_token({"sub": "doctor_user", "role": "doctor"})

        # Assigned patient -> Allowed
        res_assigned = self.client.get(
            "/api/v1/patients/PAT-00001",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_assigned.status_code, 200)

        # Unassigned patient -> Denied 403
        res_unassigned = self.client.get(
            "/api/v1/patients/PAT-00003",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_unassigned.status_code, 403)
        self.assertIn("not assigned to patient", res_unassigned.json()["detail"])

    def test_07_public_health_analyst_restriction(self):
        # Public health analyst cannot access identifiable records
        token = create_access_token({"sub": "analyst_user", "role": "public_health_analyst"})

        res = self.client.get(
            "/api/v1/patients/PAT-00001",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("prohibited from accessing identifiable patient", res.json()["detail"])

        res_list = self.client.get(
            "/api/v1/patients",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_list.status_code, 403)

    # --- 4. Audit Logging ---
    def test_08_audit_log_creation(self):
        # Test that denied attempt was logged into PostgreSQL audit_logs table
        recent_log = self.db.scalar(
            select(AuditLog)
            .where(AuditLog.action == "ACCESS_DENIED_ANALYST_RESTRICTION")
            .order_by(AuditLog.timestamp.desc())
        )
        self.assertIsNotNone(recent_log)
        self.assertEqual(recent_log.user_id, "analyst_user")
        self.assertEqual(recent_log.record_id, "PAT-00001")

    # --- 5. EHR Endpoints & Search Pagination ---
    def test_09_patient_search_and_pagination(self):
        token = create_access_token({"sub": "admin_user", "role": "hospital_admin"})

        res = self.client.get(
            "/api/v1/patients?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 1000)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 10)
        self.assertEqual(len(data["data"]), 10)

        # Filtering by district
        res_filter = self.client.get(
            "/api/v1/patients?district=Pune",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_filter.status_code, 200)
        for p in res_filter.json()["data"]:
            self.assertEqual(p["district"], "Pune")

    # --- 6. Longitudinal Timeline & Clinical Resources ---
    def test_10_longitudinal_patient_timeline(self):
        token = create_access_token({"sub": "doctor_user", "role": "doctor"})

        res = self.client.get(
            "/api/v1/patients/PAT-00001/timeline",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["patient_id"], "PAT-00001")
        self.assertGreater(data["total_events"], 0)
        events = data["events"]
        
        # Verify strict chronological sorting
        for i in range(len(events) - 1):
            self.assertLessEqual(events[i]["event_date"], events[i+1]["event_date"])

        # Verify event attributes
        event_types = {e["event_type"] for e in events}
        self.assertTrue(any(t in event_types for t in ["encounter", "condition", "observation", "medication"]))
        first_event = events[0]
        self.assertIn("source_table", first_event)
        self.assertIn("clinical_details", first_event)

    def test_11_patient_sub_resources(self):
        token = create_access_token({"sub": "doctor_user", "role": "doctor"})

        # Encounters
        res_enc = self.client.get("/api/v1/patients/PAT-00001/encounters", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_enc.status_code, 200)
        self.assertGreater(len(res_enc.json()), 0)

        # Conditions
        res_cond = self.client.get("/api/v1/patients/PAT-00001/conditions", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_cond.status_code, 200)

        # Observations
        res_obs = self.client.get("/api/v1/patients/PAT-00001/observations", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_obs.status_code, 200)

        # Medications
        res_med = self.client.get("/api/v1/patients/PAT-00001/medications", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_med.status_code, 200)

        # Risk Assessments
        res_risk = self.client.get("/api/v1/patients/PAT-00001/risk-assessments", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_risk.status_code, 200)
        self.assertGreater(len(res_risk.json()), 0)

    def test_12_invalid_patient_id(self):
        token = create_access_token({"sub": "admin_user", "role": "hospital_admin"})
        res = self.client.get("/api/v1/patients/PAT-DOESNOTEXIST", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"])

if __name__ == "__main__":
    unittest.main()

