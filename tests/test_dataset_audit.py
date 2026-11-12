"""
Automated Unit Tests for SymbiPredict Dataset Audit & Integrity
Tests:
- File existence and SHA-256 match
- Manifest metadata completeness
- Data shape, target column, feature binary constraints
- Duplicate count and leakage risk detection
- Report generation verification
"""

import json
import hashlib
from pathlib import Path
import pandas as pd
import pytest

DATA_PATH = Path("data/disease_prediction/raw/symbipredict_2022.csv")
MANIFEST_PATH = Path("data/disease_prediction/raw/dataset_manifest.json")
AUDIT_JSON_PATH = Path("reports/phase3/dataset_audit_summary.json")
AUDIT_MD_PATH = Path("reports/phase3/dataset_audit.md")

EXPECTED_SHA256 = "9834c90dd48eb2fef1fa56282f8f016a6781b0e4ada878015dc34a81af8e9e1b"
EXPECTED_SIZE = 1382907

def test_raw_dataset_file_and_checksum():
    assert DATA_PATH.exists(), f"Raw CSV missing at {DATA_PATH}"
    assert DATA_PATH.stat().st_size == EXPECTED_SIZE, "Raw CSV size mismatch"
    
    hasher = hashlib.sha256()
    with open(DATA_PATH, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    assert hasher.hexdigest() == EXPECTED_SHA256, "SHA-256 checksum mismatch"

def test_manifest_metadata():
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["doi"] == "10.17632/dv5z3v2xyd.1"
    assert manifest["license"] == "Creative Commons Attribution 4.0 International (CC BY 4.0)"
    assert manifest["sha256"] == EXPECTED_SHA256

def test_dataset_dimensions_and_target():
    df = pd.read_csv(DATA_PATH)
    assert df.shape == (4961, 133)
    assert "prognosis" in df.columns
    assert df["prognosis"].nunique() == 41
    assert df.isnull().sum().sum() == 0

def test_feature_binary_representation():
    df = pd.read_csv(DATA_PATH)
    symptom_cols = [c for c in df.columns if c != "prognosis"]
    assert len(symptom_cols) == 132
    for c in symptom_cols:
        unique_vals = set(df[c].unique())
        assert unique_vals.issubset({0, 1}), f"Column {c} has non-binary values: {unique_vals}"

def test_duplicate_and_leakage_metrics():
    assert AUDIT_JSON_PATH.exists()
    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)
    qual = summary["data_quality_and_duplicates"]
    assert qual["exact_duplicate_rows"] == 4657
    assert qual["unique_rows"] == 304
    assert qual["conflicting_symptom_patterns"] == 0
    assert summary["suitability_recommendation"] == "CONDITIONALLY_SUITABLE"

def test_audit_artifacts_exist():
    assert AUDIT_MD_PATH.exists()
    fig_dir = Path("reports/phase3/figures")
    assert (fig_dir / "disease_class_distribution.png").exists()
    assert (fig_dir / "top_20_symptoms.png").exists()
    assert (fig_dir / "symptom_burden_distribution.png").exists()
    assert (fig_dir / "duplicate_record_proportion.png").exists()

