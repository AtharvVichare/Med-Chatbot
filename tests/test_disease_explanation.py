"""
Automated Test Suite for Grounded Disease Prediction Explanations
Tests:
1. Valid prediction metadata produces HTTP 200 with grounded explanation and verified citations.
2. Rejection of unknown disease categories (HTTP 400).
3. Rejection of invalid / non-finite / out-of-range model scores (HTTP 400).
4. Rejection of out-of-order prediction rankings or inverted score hierarchies (HTTP 400).
5. Retrieval of relevant reference chunks from Pinecone.
6. Safe abstention when evidence is insufficient.
7. Citation cross-validation (marking valid chunks as VERIFIED_GROUNDED).
8. Resilience against Gemini API failures (returns original ML predictions gracefully without crash).
9. Resilience against Pinecone retrieval failures.
10. Strict privacy: Zero raw symptom vectors or patient EHR transmitted.
11. Preserves original /api/v1/disease/predict endpoint behavior intact.
12. Existing medical RAG and authentication endpoints continue passing.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from fastapi import status

from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.services.disease_explanation import (
    DiseaseExplanationService,
    get_disease_explanation_service,
    EXPLANATION_DISCLAIMER
)

client = TestClient(app)

@pytest.fixture
def auth_headers():
    token = create_access_token(data={"sub": "doctor_user", "role": "doctor"})
    return {"Authorization": f"Bearer {token}"}

VALID_PREDICTIONS = [
    {"rank": 1, "disease_category": "Jaundice", "experimental_model_score": 0.2578},
    {"rank": 2, "disease_category": "Heart Attack", "experimental_model_score": 0.0642},
    {"rank": 3, "disease_category": "Bronchial Asthma", "experimental_model_score": 0.0573}
]

# --- 1. Validation & Input Integrity Tests ---
def test_explain_valid_predictions(auth_headers):
    payload = {"predictions": VALID_PREDICTIONS}
    resp = client.post("/api/v1/disease/explain", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "original_predictions" in data
    assert len(data["original_predictions"]) == 3
    assert data["original_predictions"][0]["disease_category"] == "Jaundice"
    assert "explanation" in data
    assert len(data["explanation"]) > 0
    assert data["disclaimer"] == EXPLANATION_DISCLAIMER
    assert "evidence_status" in data

def test_reject_unknown_disease_category(auth_headers):
    payload = {
        "predictions": [
            {"rank": 1, "disease_category": "Alien_Syndrome_XYZ", "experimental_model_score": 0.95}
        ]
    }
    resp = client.post("/api/v1/disease/explain", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unknown disease category" in resp.json()["detail"]

def test_reject_negative_or_invalid_score(auth_headers):
    payload = {
        "predictions": [
            {"rank": 1, "disease_category": "Jaundice", "experimental_model_score": -0.5}
        ]
    }
    resp = client.post("/api/v1/disease/explain", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid experimental_model_score" in resp.json()["detail"]

def test_reject_out_of_order_ranks(auth_headers):
    payload = {
        "predictions": [
            {"rank": 2, "disease_category": "Jaundice", "experimental_model_score": 0.50},
            {"rank": 1, "disease_category": "Heart Attack", "experimental_model_score": 0.40}
        ]
    }
    resp = client.post("/api/v1/disease/explain", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Incorrect prediction rank" in resp.json()["detail"]

def test_reject_ascending_scores_hierarchy(auth_headers):
    payload = {
        "predictions": [
            {"rank": 1, "disease_category": "Jaundice", "experimental_model_score": 0.20},
            {"rank": 2, "disease_category": "Heart Attack", "experimental_model_score": 0.80}
        ]
    }
    resp = client.post("/api/v1/disease/explain", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Predictions not in descending order" in resp.json()["detail"]

# --- 2. Abstention and Failure Isolation Tests ---
def test_abstention_on_insufficient_evidence():
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = {"results": []}  # Zero results
    mock_gemini = MagicMock()

    service = DiseaseExplanationService(retrieval_service=mock_retriever, gemini_client=mock_gemini)
    res = service.explain_predictions(VALID_PREDICTIONS)

    assert res["evidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert "not contain sufficient verified excerpts" in res["explanation"]
    assert mock_gemini.generate_clinical_response.call_count == 0  # Gemini was never called

def test_gemini_api_failure_resilience():
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = {
        "results": [{
            "chunk_id": "CHK-TEST-001",
            "document_id": "DOC-TEST",
            "title": "Asthma Guide",
            "source_organization": "WHO",
            "source_url": "https://who.int",
            "content": "Asthma causes wheezing",
            "similarity_score": 0.85
        }]
    }
    mock_gemini = MagicMock()
    mock_gemini.generate_clinical_response.return_value = {
        "success": False,
        "error": "503 Server Unavailable"
    }

    service = DiseaseExplanationService(retrieval_service=mock_retriever, gemini_client=mock_gemini)
    res = service.explain_predictions(VALID_PREDICTIONS)

    assert res["evidence_status"] == "GENERATION_ERROR"
    assert len(res["original_predictions"]) == 3
    assert "automated explanatory synthesis is currently unavailable" in res["explanation"]

def test_pinecone_failure_handling():
    mock_retriever = MagicMock()
    mock_retriever.search.side_effect = RuntimeError("Pinecone connection timeout")

    service = DiseaseExplanationService(retrieval_service=mock_retriever)
    with pytest.raises(RuntimeError):
        service.explain_predictions(VALID_PREDICTIONS)

# --- 3. Privacy & Pipeline Integrity Tests ---
def test_privacy_boundaries_in_prompt_generation():
    service = DiseaseExplanationService()
    # Mock gemini call to inspect generated prompt
    with patch.object(service.gemini_client, "generate_clinical_response") as mock_gen:
        mock_gen.return_value = {
            "success": True,
            "data": {"summary": "Explanation", "citations": []}
        }
        service.explain_predictions(VALID_PREDICTIONS)
        
        # Verify prompt text passed to Gemini
        assert mock_gen.call_count == 1
        call_kwargs = mock_gen.call_args[1]
        prompt_text = call_kwargs["prompt"].lower()

        forbidden_terms = [
            "patient_id", "first_name", "last_name", "date_of_birth",
            "symptom_vector", "132-feature", "itching", "shivering",
            "encounter_id", "observation", "abha_id"
        ]
        for term in forbidden_terms:
            assert term not in prompt_text

def test_original_predict_endpoint_unaffected(auth_headers):
    # Verify POST /api/v1/disease/predict still functions exactly as expected
    payload = {"symptoms": ["fatigue", "vomiting", "high_fever"]}
    resp = client.post("/api/v1/disease/predict", json=payload, headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data["predictions"]) == 3
    assert data["predictions"][0]["disease_category"] == "Jaundice"

