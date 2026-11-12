# Aarogya Drishti 2.0 — Phase 3, Task 3.2
## Leakage-Safe Deduplication and Dataset Partitioning Report

**Raw Dataset:** `symbipredict_2022.csv`  
**Processed Directory:** `data/disease_prediction/processed/`  
**Seed:** `42`  

---

## 1. Deduplication Analysis

* **Original Raw Records:** 4,961 rows
* **Deduplicated Records:** **304 rows**
* **Duplicate Rows Removed:** 4,657 (93.87%)
* **Symptom Features:** 132 binary columns
* **Target Feature:** `prognosis`
* **Conflicting Patterns (Identical Features, Different Target):** 0

---

## 2. Per-Class Feasibility Analysis

* **Total Classes:** 41
* **Unique Patterns per Class:**
  * Minimum: 5 patterns
  * Maximum: 10 patterns
  * Mean: 7.41 patterns
* **Feasibility Thresholds:**
  * Classes with < 3 unique patterns: **0**
  * Classes with < 5 unique patterns: **0**
  * Classes with < 10 unique patterns: **37** (37 of 41 classes have between 5 and 9 patterns)

> [!NOTE]
> Standard scikit-learn `train_test_split(stratify=...)` fails with a `ValueError` because 5 classes have only 5 samples, meaning a standard two-stage random split reduces validation/test subsets to single-member groups.
> We resolved this rigorously with a **Per-Class Controlled Stratification Algorithm** that guarantees each of the 41 classes is represented in Train (3–7 samples), Validation (1–2 samples), and Test (1–2 samples).

---

## 3. Leakage-Safe Splitting Results

| Partition | Sample Count | Percentage | Classes Represented | Vector Overlap with Other Splits |
| :--- | :--- | :--- | :--- | :--- |
| **Train Set** | **214** | **70.39%** | **41 / 41 (100%)** | **0 (Zero Overlap)** |
| **Validation Set** | **45** | **14.8%** | **41 / 41 (100%)** | **0 (Zero Overlap)** |
| **Test Set (Held-Out)** | **45** | **14.8%** | **41 / 41 (100%)** | **0 (Zero Overlap)** |
| **Total Deduplicated** | **304** | **100.0%** | **41 / 41 (100%)** | — |

* **Train-Val Overlap:** 0
* **Train-Test Overlap:** 0
* **Val-Test Overlap:** 0
* **Leakage Status:** **VERIFIED LEAKAGE-FREE**

---

## 4. Key Limitations & Methodological Implications

1. **Severe Information Condensation:** The entire 4,961-row dataset condenses to 304 unique clinical patterns.
2. **Small Validation/Test Sample Size:** Because each class has 1–2 test instances, a single misclassification changes a class's recall by 50% or 100%. Macro-averaged metrics must be interpreted with this granularity in mind.
3. **No Target Leakage:** Verified that no symptom column contains prognosis tokens or trivial single-feature determinants.
