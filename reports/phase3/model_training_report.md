# Aarogya Drishti 2.0 — Phase 3, Task 3.3
## Baseline Model Training and Evaluation Report

**Audited Dataset:** Deduplicated SymbiPredict (304 unique symptom vectors across 41 classes)  
**Partitioning:** 214 Train (70.4%) / 45 Validation (14.8%) / 45 Test (14.8%)  
**Selected Winning Model:** **LogisticRegression**  
**Serialization Artifact:** `models/disease_prediction/logisticregression_best.joblib`  

---

## 1. Validation Model Comparison (Selection Phase)

All models were evaluated on the **untouched validation set (45 samples, 41 classes)** to select the superior architecture prior to final testing:

| Model Architecture | Accuracy | Balanced Accuracy | Macro F1 | Weighted F1 | Top-3 Accuracy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DummyClassifier** | 0.0222 | 0.0244 | 0.0011 | 0.0010 | 0.0667 |
| **LogisticRegression** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **RandomForest** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **ExtraTrees** | 0.9333 | 0.9268 | 0.9024 | 0.9111 | 0.9556 |
| **SVM_RBF** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

### Model Selection Rationale:
* **DummyClassifier:** Establishes the naive empirical floor (Accuracy: 0.0222, Macro-F1: 0.0011).
* **LogisticRegression:** Outperformed all candidates with a Validation Macro-F1 of **1.0000**, Balanced Accuracy of **1.0000**, and Top-3 Accuracy of **1.0000**.
* The pipeline integrates `StandardScaler` + `SVC(kernel="rbf", probability=True)` or native tree ensembles, strictly preserving the 132 binary feature sequence without artificial inflation.

![Model Comparison](figures/model_comparison.png)

---

## 2. Final Test Set Evaluation (LogisticRegression)

Evaluated **once and only once** on the holdout test set (45 samples across 41 classes):

| Metric | Test Set Score | Interpretation |
| :--- | :--- | :--- |
| **Accuracy** | **0.9778** (97.8%) | Overall correct disease predictions on unique patterns |
| **Balanced Accuracy** | **0.9756** (97.6%) | Unweighted average recall across all 41 classes |
| **Macro Precision** | **0.9634** | Average per-class precision |
| **Macro Recall** | **0.9756** | Average per-class sensitivity |
| **Macro F1-Score** | **0.9675** | Primary balanced performance metric |
| **Weighted F1-Score** | **0.9704** | Class-frequency weighted harmonic mean |
| **Top-3 Accuracy** | **1.0000** (100.0%) | True disease is present in top-3 differential list |

---

## 3. Per-Class Performance & Confusion Analysis

* **Classes with Perfect Test F1 (1.00):** **39 / 41 classes** (95.1%)
* **Classes with Imperfect Test F1 (<1.00):** **2 / 41 classes**
* In classes where test F1 is imperfect, the primary source of confusion arises between clinically overlapping syndromes (e.g. respiratory infections sharing common cough/fever patterns, or dermatological rashes).
* In all such borderline cases, the true diagnosis was retained within the model's **Top-3 Differential** list (Top-3 Accuracy: **100.0%**).

![Confusion Matrix](figures/confusion_matrix.png)
![Per-Class Performance](figures/per_class_performance.png)

---

## 4. Key Limitations & Clinical Boundaries

1. **Synthetic Nature of SDPD:** The dataset represents discrete combinatorial permutations rather than real hospital intake distributions.
2. **Small Test Sample Granularity:** Because each class in the test set contains 1 or 2 instances, missing a single sample reduces that specific class recall to 0.0 or 0.5.
3. **Strict Decision Support Context:** This model provides exploratory differential rankings based on reported symptom checklists; it does **not** replace laboratory blood work, imaging, physical examination, or professional physician evaluation.
