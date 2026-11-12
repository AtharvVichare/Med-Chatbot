"""
Automated Test Suite for Preprocessing and Baseline Model Training
Tests:
- Deduplication correctness (raw 4,961 -> 304 deduplicated)
- Feature-target separation (132 features, 1 prognosis target)
- Reproducible per-class stratified splitting
- Zero overlapping symptom vectors between Train, Val, and Test
- Feature column order preservation (exactly 132 features)
- Model artifact loading and structure
- Prediction output dimensions (predict and predict_proba)
- Valid probability distributions (sum to 1.0, non-negative)
"""

import json
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
import pytest

from src.disease_prediction.preprocessing import DatasetPreprocessor

PROCESSED_DIR = Path("data/disease_prediction/processed")
MODEL_PATH = Path("models/disease_prediction/logisticregression_best.joblib")
METADATA_PATH = Path("models/disease_prediction/logisticregression_metadata.json")

def test_deduplication_correctness():
    preprocessor = DatasetPreprocessor()
    raw_df, dedup_df, stats = preprocessor.load_and_deduplicate()
    
    assert len(raw_df) == 4961
    assert len(dedup_df) == 304
    assert stats["conflicting_patterns_count"] == 0
    assert stats["total_classes"] == 41

def test_split_reproducibility_and_proportions():
    preprocessor = DatasetPreprocessor(seed=42)
    raw_df, dedup_df, stats = preprocessor.load_and_deduplicate()
    train_df, val_df, test_df, split = preprocessor.create_leakage_safe_split(dedup_df)
    
    assert len(train_df) == 214
    assert len(val_df) == 45
    assert len(test_df) == 45
    assert split["train_classes_represented"] == 41
    assert split["val_classes_represented"] == 41
    assert split["test_classes_represented"] == 41

def test_zero_vector_overlap_across_splits():
    train_df = pd.read_csv(PROCESSED_DIR / "train.csv")
    val_df = pd.read_csv(PROCESSED_DIR / "val.csv")
    test_df = pd.read_csv(PROCESSED_DIR / "test.csv")
    
    symptom_cols = [c for c in train_df.columns if c != "prognosis"]
    assert len(symptom_cols) == 132
    
    train_tuples = set(tuple(x) for x in train_df[symptom_cols].to_numpy())
    val_tuples = set(tuple(x) for x in val_df[symptom_cols].to_numpy())
    test_tuples = set(tuple(x) for x in test_df[symptom_cols].to_numpy())
    
    assert len(train_tuples.intersection(val_tuples)) == 0, "Leakage detected between Train and Val"
    assert len(train_tuples.intersection(test_tuples)) == 0, "Leakage detected between Train and Test"
    assert len(val_tuples.intersection(test_tuples)) == 0, "Leakage detected between Val and Test"

def test_model_artifact_load_and_structure():
    assert MODEL_PATH.exists()
    assert METADATA_PATH.exists()
    
    bundle = joblib.load(MODEL_PATH)
    assert "pipeline" in bundle
    assert "feature_names" in bundle
    assert "classes" in bundle
    assert len(bundle["feature_names"]) == 132
    assert len(bundle["classes"]) == 41

def test_model_prediction_and_probability_properties():
    bundle = joblib.load(MODEL_PATH)
    pipeline = bundle["pipeline"]
    feature_names = bundle["feature_names"]
    classes = np.array(bundle["classes"])
    
    # Test with dummy zero vector (all symptoms absent)
    zero_vector = np.zeros((1, 132))
    pred = pipeline.predict(zero_vector)
    assert len(pred) == 1
    assert pred[0] in classes
    
    # Test probabilities
    proba = pipeline.predict_proba(zero_vector)
    assert proba.shape == (1, 41)
    assert np.all(proba >= 0.0)
    assert np.isclose(np.sum(proba), 1.0, atol=1e-5)
    
    # Test batch predictions on test set
    test_df = pd.read_csv(PROCESSED_DIR / "test.csv")
    X_test = test_df[feature_names].to_numpy()
    batch_preds = pipeline.predict(X_test)
    assert len(batch_preds) == len(X_test)
    
    batch_proba = pipeline.predict_proba(X_test)
    assert batch_proba.shape == (len(X_test), 41)
    row_sums = np.sum(batch_proba, axis=1)
    assert np.all(np.isclose(row_sums, 1.0, atol=1e-5))

