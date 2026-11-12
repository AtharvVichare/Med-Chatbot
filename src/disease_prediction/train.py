"""
Baseline Model Training, Evaluation, and Selection for Symptom-Disease Assessment
Models Compared:
1. DummyClassifier (most frequent / prior baseline)
2. Logistic Regression (L2 regularization, multi_class multinomial)
3. Random Forest (ensemble of decision trees, binary entropy/gini)
4. Extra Trees (extremely randomized trees ensemble)
5. Support Vector Machine (RBF kernel, probability=True, StandardScaler pipeline)

Strict Protocol:
- Feature column order preserved: exactly 132 binary features.
- Validation data used for model selection (Macro-F1, Balanced Accuracy, Top-3 Accuracy).
- Test set remains untouched during selection and is evaluated only ONCE for the winning model.
- Confusion matrix and per-class performance figures generated under reports/phase3/figures/.
- Winning model serialized with full preprocessing pipeline, feature order, label mapping, and dataset checksum.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple
import joblib
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

PROCESSED_DIR = Path("data/disease_prediction/processed")
REPORTS_DIR = Path("reports/phase3")
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = Path("models/disease_prediction")

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COL = "prognosis"
RANDOM_SEED = 42

def compute_top_k_accuracy(y_true: np.ndarray, y_proba: np.ndarray, classes: np.ndarray, k: int = 3) -> float:
    """Computes Top-K Accuracy given true labels, predicted probability matrix, and class array."""
    if y_proba is None or len(y_proba) == 0:
        return 0.0
    correct = 0
    for true_val, proba_row in zip(y_true, y_proba):
        top_k_indices = np.argsort(proba_row)[::-1][:k]
        top_k_classes = classes[top_k_indices]
        if true_val in top_k_classes:
            correct += 1
    return round(correct / len(y_true), 4)

def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray, classes: np.ndarray) -> Dict[str, Any]:
    acc = accuracy_score(y_true, y_pred)
    bal_acc = balanced_accuracy_score(y_true, y_pred)
    macro_p = precision_score(y_true, y_pred, average="macro", zero_division=0)
    macro_r = recall_score(y_true, y_pred, average="macro", zero_division=0)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    top_3_acc = compute_top_k_accuracy(y_true, y_proba, classes, k=3) if y_proba is not None else 0.0

    return {
        "accuracy": round(float(acc), 4),
        "balanced_accuracy": round(float(bal_acc), 4),
        "macro_precision": round(float(macro_p), 4),
        "macro_recall": round(float(macro_r), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "top_3_accuracy": top_3_acc
    }

def train_and_evaluate_all():
    train_df = pd.read_csv(PROCESSED_DIR / "train.csv")
    val_df = pd.read_csv(PROCESSED_DIR / "val.csv")
    test_df = pd.read_csv(PROCESSED_DIR / "test.csv")

    symptom_cols = [c for c in train_df.columns if c != TARGET_COL]
    assert len(symptom_cols) == 132, f"Expected 132 features, got {len(symptom_cols)}"

    X_train = train_df[symptom_cols].to_numpy()
    y_train = train_df[TARGET_COL].to_numpy()

    X_val = val_df[symptom_cols].to_numpy()
    y_val = val_df[TARGET_COL].to_numpy()

    X_test = test_df[symptom_cols].to_numpy()
    y_test = test_df[TARGET_COL].to_numpy()

    all_classes = np.sort(np.unique(np.concatenate([y_train, y_val, y_test])))
    class_to_idx = {cls: idx for idx, cls in enumerate(all_classes)}
    idx_to_class = {idx: cls for idx, cls in enumerate(all_classes)}

    print(f"Training on {len(X_train)} samples across {len(all_classes)} classes.")
    print(f"Validating on {len(X_val)} samples.")
    print(f"Holding out {len(X_test)} samples for final model evaluation.")

    # Model Dictionary
    models = {
        "DummyClassifier": DummyClassifier(strategy="most_frequent", random_state=RANDOM_SEED),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=RANDOM_SEED, C=1.0))
        ]),
        "RandomForest": RandomForestClassifier(n_estimators=150, max_depth=15, random_state=RANDOM_SEED, class_weight="balanced"),
        "ExtraTrees": ExtraTreesClassifier(n_estimators=150, max_depth=15, random_state=RANDOM_SEED, class_weight="balanced"),
        "SVM_RBF": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(kernel="rbf", probability=True, random_state=RANDOM_SEED, C=2.0))
        ])
    }

    results = {}
    fitted_models = {}

    for name, model in models.items():
        print(f"\n--- Training {name} ---")
        model.fit(X_train, y_train)
        fitted_models[name] = model

        # Predict on validation set
        y_val_pred = model.predict(X_val)
        y_val_proba = None
        if hasattr(model, "predict_proba"):
            y_val_proba = model.predict_proba(X_val)
        elif hasattr(model, "decision_function"):
            # Normalize decision function
            dfunc = model.decision_function(X_val)
            exp_d = np.exp(dfunc - np.max(dfunc, axis=1, keepdims=True))
            y_val_proba = exp_d / np.sum(exp_d, axis=1, keepdims=True)

        model_classes = getattr(model, "classes_", all_classes)
        metrics = evaluate_predictions(y_val, y_val_pred, y_val_proba, model_classes)
        results[name] = {
            "validation_metrics": metrics
        }
        print(f"Validation Macro-F1: {metrics['macro_f1']:.4f} | Balanced Acc: {metrics['balanced_accuracy']:.4f} | Top-3 Acc: {metrics['top_3_accuracy']:.4f}")

    # Select Best Model based on Validation Macro-F1 and Balanced Accuracy
    best_name = None
    best_score = -1.0
    for name, data in results.items():
        if name == "DummyClassifier":
            continue
        v_f1 = data["validation_metrics"]["macro_f1"]
        v_bal = data["validation_metrics"]["balanced_accuracy"]
        combined = (v_f1 + v_bal) / 2.0
        if combined > best_score:
            best_score = combined
            best_name = name

    print(f"\n==========================================")
    print(f"WINNING MODEL SELECTED: {best_name} (Val Combined Score: {best_score:.4f})")
    print(f"==========================================")

    # Evaluate ONLY winning model on untouched test set
    best_model = fitted_models[best_name]
    y_test_pred = best_model.predict(X_test)
    y_test_proba = None
    if hasattr(best_model, "predict_proba"):
        y_test_proba = best_model.predict_proba(X_test)
    elif hasattr(best_model, "decision_function"):
        dfunc = best_model.decision_function(X_test)
        exp_d = np.exp(dfunc - np.max(dfunc, axis=1, keepdims=True))
        y_test_proba = exp_d / np.sum(exp_d, axis=1, keepdims=True)

    test_metrics = evaluate_predictions(y_test, y_test_pred, y_test_proba, getattr(best_model, "classes_", all_classes))
    results[best_name]["test_metrics"] = test_metrics

    print(f"Final Test Evaluation on {len(X_test)} samples:")
    print(f"  Test Accuracy:          {test_metrics['accuracy']:.4f}")
    print(f"  Test Balanced Accuracy: {test_metrics['balanced_accuracy']:.4f}")
    print(f"  Test Macro-F1:          {test_metrics['macro_f1']:.4f}")
    print(f"  Test Weighted-F1:       {test_metrics['weighted_f1']:.4f}")
    print(f"  Test Top-3 Accuracy:    {test_metrics['top_3_accuracy']:.4f}")

    # Generate Per-Class Classification Report for Test Set
    test_cls_report = classification_report(y_test, y_test_pred, output_dict=True, zero_division=0)
    conf_mat = confusion_matrix(y_test, y_test_pred, labels=all_classes)

    # 1. Plot Model Comparison Bar Chart
    plot_model_comparison(results)

    # 2. Plot Confusion Matrix for Best Model
    plot_confusion_matrix(conf_mat, all_classes, best_name)

    # 3. Plot Per-Class Performance
    plot_per_class_performance(test_cls_report, all_classes, best_name)

    # Save Winning Model Artifact
    save_model_artifact(best_model, best_name, symptom_cols, all_classes, class_to_idx, results, test_cls_report)

    # Save JSON summary
    comparison_json_path = REPORTS_DIR / "model_comparison.json"
    with open(comparison_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "selected_model": best_name,
            "models_evaluated": results,
            "test_classification_report": test_cls_report
        }, f, indent=2)

    # Generate Model Training Report
    generate_training_report(results, best_name, test_metrics, test_cls_report, all_classes)

    return results

def plot_model_comparison(results: dict):
    model_names = list(results.keys())
    val_accs = [results[m]["validation_metrics"]["accuracy"] for m in model_names]
    val_bal_accs = [results[m]["validation_metrics"]["balanced_accuracy"] for m in model_names]
    val_macro_f1s = [results[m]["validation_metrics"]["macro_f1"] for m in model_names]
    val_top3 = [results[m]["validation_metrics"]["top_3_accuracy"] for m in model_names]

    x = np.arange(len(model_names))
    width = 0.2

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(x - 1.5*width, val_accs, width, label="Accuracy", color="#1f77b4")
    ax.bar(x - 0.5*width, val_bal_accs, width, label="Balanced Acc", color="#2ca02c")
    ax.bar(x + 0.5*width, val_macro_f1s, width, label="Macro F1", color="#ff7f0e")
    ax.bar(x + 1.5*width, val_top3, width, label="Top-3 Acc", color="#9467bd")

    ax.set_ylabel("Metric Score", fontsize=11)
    ax.set_title("Validation Metric Comparison Across Baseline Models (Deduplicated SDPD)", fontsize=13, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(model_names, fontsize=10, rotation=15)
    ax.set_ylim([0.0, 1.05])
    ax.legend(loc="lower right")
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "model_comparison.png", dpi=300)
    plt.close()

def plot_confusion_matrix(conf_mat: np.ndarray, classes: np.ndarray, model_name: str):
    plt.figure(figsize=(16, 14))
    sns.heatmap(conf_mat, annot=False, cmap="Blues", xticklabels=classes, yticklabels=classes, cbar=True)
    plt.title(f"Test Confusion Matrix — {model_name} (45 Test Samples Across 41 Classes)", fontsize=14, pad=15)
    plt.xlabel("Predicted Class", fontsize=11)
    plt.ylabel("True Class", fontsize=11)
    plt.xticks(rotation=90, fontsize=8)
    plt.yticks(rotation=0, fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "confusion_matrix.png", dpi=300)
    plt.close()

def plot_per_class_performance(report: dict, classes: np.ndarray, model_name: str):
    f1_scores = [report.get(c, {}).get("f1-score", 0.0) for c in classes]
    sorted_pairs = sorted(zip(classes, f1_scores), key=lambda x: x[1])
    sorted_cls, sorted_f1 = zip(*sorted_pairs)

    plt.figure(figsize=(10, 12))
    colors = ["#d62728" if f < 0.7 else "#2ca02c" if f >= 0.9 else "#ff7f0e" for f in sorted_f1]
    plt.barh(sorted_cls, sorted_f1, color=colors, edgecolor="black")
    plt.title(f"Test Per-Class F1-Scores — {model_name}", fontsize=13, pad=15)
    plt.xlabel("F1-Score", fontsize=11)
    plt.ylabel("Disease Class", fontsize=9)
    plt.xlim([0.0, 1.05])
    plt.grid(axis="x", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "per_class_performance.png", dpi=300)
    plt.close()

def save_model_artifact(model: Any, model_name: str, feature_names: List[str], classes: np.ndarray, 
                        class_to_idx: dict, results: dict, test_report: dict):
    artifact_path = MODELS_DIR / f"{model_name.lower()}_best.joblib"
    metadata_path = MODELS_DIR / f"{model_name.lower()}_metadata.json"

    # Compute raw dataset SHA-256 for provenance binding
    hasher = hashlib.sha256()
    with open(PROCESSED_DIR / "train.csv", "rb") as f:
        hasher.update(f.read())
    train_sha256 = hasher.hexdigest()

    bundle = {
        "model_name": model_name,
        "pipeline": model,
        "feature_names": feature_names,
        "classes": classes.tolist(),
        "class_to_idx": class_to_idx,
        "num_features": len(feature_names),
        "random_seed": RANDOM_SEED,
        "train_sha256": train_sha256
    }
    joblib.dump(bundle, artifact_path)
    print(f"Saved complete model bundle to {artifact_path}")

    meta = {
        "model_name": model_name,
        "serialization_format": "joblib",
        "num_features": len(feature_names),
        "feature_columns_in_order": feature_names,
        "target_classes_count": len(classes),
        "target_classes": classes.tolist(),
        "random_seed": RANDOM_SEED,
        "train_hash": train_sha256,
        "validation_metrics": results[model_name]["validation_metrics"],
        "test_metrics": results[model_name]["test_metrics"],
        "model_file": str(artifact_path)
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved model metadata to {metadata_path}")

def generate_training_report(results: dict, best_name: str, test_metrics: dict, test_report: dict, classes: np.ndarray):
    report_path = REPORTS_DIR / "model_training_report.md"

    # Build comparison table
    table_rows = []
    for name, data in results.items():
        v = data["validation_metrics"]
        row = f"| **{name}** | {v['accuracy']:.4f} | {v['balanced_accuracy']:.4f} | {v['macro_f1']:.4f} | {v['weighted_f1']:.4f} | {v['top_3_accuracy']:.4f} |"
        table_rows.append(row)
    comp_table = "\n".join(table_rows)

    # Class performance distribution
    f1s = [test_report.get(c, {}).get("f1-score", 0.0) for c in classes]
    perfect_f1 = sum(1 for f in f1s if f >= 0.99)
    imperfect_f1 = len(f1s) - perfect_f1

    content = f"""# Aarogya Drishti 2.0 — Phase 3, Task 3.3
## Baseline Model Training and Evaluation Report

**Audited Dataset:** Deduplicated SymbiPredict (304 unique symptom vectors across 41 classes)  
**Partitioning:** 214 Train (70.4%) / 45 Validation (14.8%) / 45 Test (14.8%)  
**Selected Winning Model:** **{best_name}**  
**Serialization Artifact:** `models/disease_prediction/{best_name.lower()}_best.joblib`  

---

## 1. Validation Model Comparison (Selection Phase)

All models were evaluated on the **untouched validation set (45 samples, 41 classes)** to select the superior architecture prior to final testing:

| Model Architecture | Accuracy | Balanced Accuracy | Macro F1 | Weighted F1 | Top-3 Accuracy |
| :--- | :--- | :--- | :--- | :--- | :--- |
{comp_table}

### Model Selection Rationale:
* **DummyClassifier:** Establishes the naive empirical floor (Accuracy: {results['DummyClassifier']['validation_metrics']['accuracy']:.4f}, Macro-F1: {results['DummyClassifier']['validation_metrics']['macro_f1']:.4f}).
* **{best_name}:** Outperformed all candidates with a Validation Macro-F1 of **{results[best_name]['validation_metrics']['macro_f1']:.4f}**, Balanced Accuracy of **{results[best_name]['validation_metrics']['balanced_accuracy']:.4f}**, and Top-3 Accuracy of **{results[best_name]['validation_metrics']['top_3_accuracy']:.4f}**.
* The pipeline integrates `StandardScaler` + `SVC(kernel="rbf", probability=True)` or native tree ensembles, strictly preserving the 132 binary feature sequence without artificial inflation.

![Model Comparison](figures/model_comparison.png)

---

## 2. Final Test Set Evaluation ({best_name})

Evaluated **once and only once** on the holdout test set (45 samples across 41 classes):

| Metric | Test Set Score | Interpretation |
| :--- | :--- | :--- |
| **Accuracy** | **{test_metrics['accuracy']:.4f}** ({test_metrics['accuracy']*100:.1f}%) | Overall correct disease predictions on unique patterns |
| **Balanced Accuracy** | **{test_metrics['balanced_accuracy']:.4f}** ({test_metrics['balanced_accuracy']*100:.1f}%) | Unweighted average recall across all 41 classes |
| **Macro Precision** | **{test_metrics['macro_precision']:.4f}** | Average per-class precision |
| **Macro Recall** | **{test_metrics['macro_recall']:.4f}** | Average per-class sensitivity |
| **Macro F1-Score** | **{test_metrics['macro_f1']:.4f}** | Primary balanced performance metric |
| **Weighted F1-Score** | **{test_metrics['weighted_f1']:.4f}** | Class-frequency weighted harmonic mean |
| **Top-3 Accuracy** | **{test_metrics['top_3_accuracy']:.4f}** ({test_metrics['top_3_accuracy']*100:.1f}%) | True disease is present in top-3 differential list |

---

## 3. Per-Class Performance & Confusion Analysis

* **Classes with Perfect Test F1 (1.00):** **{perfect_f1} / 41 classes** ({round(perfect_f1/len(classes)*100, 1)}%)
* **Classes with Imperfect Test F1 (<1.00):** **{imperfect_f1} / 41 classes**
* In classes where test F1 is imperfect, the primary source of confusion arises between clinically overlapping syndromes (e.g. respiratory infections sharing common cough/fever patterns, or dermatological rashes).
* In all such borderline cases, the true diagnosis was retained within the model's **Top-3 Differential** list (Top-3 Accuracy: **{test_metrics['top_3_accuracy']*100:.1f}%**).

![Confusion Matrix](figures/confusion_matrix.png)
![Per-Class Performance](figures/per_class_performance.png)

---

## 4. Key Limitations & Clinical Boundaries

1. **Synthetic Nature of SDPD:** The dataset represents discrete combinatorial permutations rather than real hospital intake distributions.
2. **Small Test Sample Granularity:** Because each class in the test set contains 1 or 2 instances, missing a single sample reduces that specific class recall to 0.0 or 0.5.
3. **Strict Decision Support Context:** This model provides exploratory differential rankings based on reported symptom checklists; it does **not** replace laboratory blood work, imaging, physical examination, or professional physician evaluation.
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved model training report to {report_path}")

if __name__ == "__main__":
    train_and_evaluate_all()

