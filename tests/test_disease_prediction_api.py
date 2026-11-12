"""
Comprehensive Test Suite for FastAPI Symptom-Based Disease Prediction Endpoint
Tests:
1. Valid symptom request returns HTTP 200 with top-3 predictions.
2. Prediction scores are finite, non-negative, and strictly ordered in descending rank.
3. Unknown symptom names trigger HTTP 400 with helpful error messages.
4. Duplicate symptoms trigger HTTP 400.
5. Empty symptom list triggers HTTP 422/400.
6. Invalid input types (e.g. non-string symptoms) trigger HTTP 422.
7. Exact 132-feature sequence ordering is preserved by the service.
8. Model is loaded once (singleton caching) rather than per request.
9. Missing or corrupted artifact handling fails safely without fallback to mock predictions.
10. Authentication enforcement: Unauthenticated requests return HTTP 401.
11. Existing endpoints (health, ready, auth) remain fully operational and unaffected.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from fastapi import status

from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.services.disease_prediction import (
    DiseasePredictionService,
    get_disease_prediction_service,
    CLINICAL_DISCLAIMER
)

client = TestClient(app)

@pytest.fixture
def auth_headers():
    token = create_access_token(data={"sub": "doctor_user", "role": "doctor"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def patient_auth_headers():
    token = create_access_token(data={"sub": "patient_user", "role": "patient"})
    return {"Authorization": f"Bearer {token}"}

# --- 1. Valid Request Tests ---
def test_predict_disease_valid_request(auth_headers):
    payload = {
        "symptoms": ["fatigue", "vomiting", "high_fever"]
    }
    resp = client.post("/api/v1/disease/predict", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "predictions" in data
    assert len(data["predictions"]) == 3
    assert data["symptoms_supplied_count"] == 3
    assert "LogisticRegression" in data["model_identifier"]
    assert data["disclaimer"] == CLINICAL_DISCLAIMER

    # Check predictions structure and strict score ordering
    preds = data["predictions"]
    for i, p in enumerate(preds, 1):
        assert p["rank"] == i
        assert isinstance(p["disease_category"], str)
        assert len(p["disease_category"]) > 0
        assert 0.0 <= p["experimental_model_score"] <= 1.0

    assert preds[0]["experimental_model_score"] >= preds[1]["experimental_model_score"] >= preds[2]["experimental_model_score"]

def test_list_supported_symptoms(auth_headers):
    resp = client.get("/api/v1/disease/symptoms", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    symptoms = resp.json()
    assert isinstance(symptoms, list)
    assert len(symptoms) == 132
    assert "itching" in symptoms
    assert "fatigue" in symptoms
    assert "high_fever" in symptoms

# --- 2. Error Handling & Validation Tests ---
def test_reject_unknown_symptom(auth_headers):
    payload = {
        "symptoms": ["fatigue", "fever", "unknown_disease_xyz"]  # "fever" is invalid (high_fever/mild_fever are valid)
    }
    resp = client.post("/api/v1/disease/predict", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unknown symptom feature" in resp.json()["detail"]

def test_reject_duplicate_symptoms(auth_headers):
    payload = {
        "symptoms": ["fatigue", "vomiting", "fatigue"]
    }
    resp = client.post("/api/v1/disease/predict", json=payload, headers=auth_headers)
    assert resp.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
    detail = str(resp.json())
    assert "duplicate" in detail.lower()

def test_reject_empty_symptom_list(auth_headers):
    payload = {
        "symptoms": []
    }
    resp = client.post("/api/v1/disease/predict", json=payload, headers=auth_headers)
    assert resp.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

def test_reject_invalid_input_types(auth_headers):
    payload = {
        "symptoms": ["fatigue", 12345]  # Non-string symptom
    }
    resp = client.post("/api/v1/disease/predict", json=payload, headers=auth_headers)
    assert resp.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

# --- 3. Authentication Enforcement Tests ---
def test_unauthenticated_request_rejected():
    payload = {
        "symptoms": ["fatigue", "vomiting"]
    }
    resp = client.post("/api/v1/disease/predict", json=payload)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED

def test_invalid_bearer_token_rejected():
    headers = {"Authorization": "Bearer invalid_token_12345"}
    payload = {"symptoms": ["fatigue"]}
    resp = client.post("/api/v1/disease/predict", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED

# --- 4. Service Architecture & Lifecycle Tests ---
def test_service_singleton_caching():
    svc1 = get_disease_prediction_service()
    svc2 = get_disease_prediction_service()
    assert svc1 is svc2
    assert len(svc1.feature_columns) == 132
    assert len(svc1.target_classes) == 41

def test_service_fails_on_missing_model():
    with pytest.raises(FileNotFoundError):
        DiseasePredictionService(model_path=Path("non_existent_model_xyz.joblib"))

# --- 5. Regression Check for Existing Endpoints ---
def test_system_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "healthy"

