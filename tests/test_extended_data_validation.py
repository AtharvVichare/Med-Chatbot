"""
Extended Data Validation Test Suite
Updated to reflect:
- WHO/ISH SEAR-D model explicitly documented as a heuristic simulation (not clinically certified)
- Real-world clinical chronology: chronic condition onset dates can precede registration at current clinic;
  encounters >= registration; observations and prescriptions aligned with encounters.
- Synthetic identifier checking (internal SYNTH-ID prefix, avoiding confusion with official NHA ABHAs)
- Numeric measurement typing & synthetic metadata
"""

import csv
import json
from datetime import datetime
from pathlib import Path
import unittest

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"

def load_csv(filename):
    filepath = SYNTHETIC_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"File {filename} does not exist!")
    with open(filepath, mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

class TestExtendedDataValidation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.patients = load_csv("patients.csv")
        cls.encounters = load_csv("encounters.csv")
        cls.conditions = load_csv("conditions.csv")
        cls.observations = load_csv("observations.csv")
        cls.medications = load_csv("medications.csv")
        cls.risk_assessments = load_csv("risk_assessments.csv")
        cls.audit_logs = load_csv("audit_logs.csv")
        
        with open(DATA_DIR / "reference_manifest.json", "r", encoding="utf-8") as f:
            cls.manifest = json.load(f)

    # 1. Verify Patient IDs and Foreign Key Relationships
    def test_patient_ids_and_foreign_keys(self):
        patient_ids = {p["patient_id"] for p in self.patients}
        self.assertEqual(len(patient_ids), 1000, "All 1000 patients must have unique IDs")
        
        # Check encounters foreign keys
        encounter_ids = set()
        for enc in self.encounters:
            self.assertIn(enc["patient_id"], patient_ids, f"Orphan encounter: {enc['encounter_id']}")
            encounter_ids.add(enc["encounter_id"])
        self.assertEqual(len(encounter_ids), len(self.encounters), "Encounter IDs must be unique")

        # Check conditions foreign keys
        for cond in self.conditions:
            self.assertIn(cond["patient_id"], patient_ids, f"Orphan condition: {cond['condition_id']}")

        # Check observations foreign keys (both patient_id and encounter_id)
        for obs in self.observations:
            self.assertIn(obs["patient_id"], patient_ids, f"Orphan observation patient: {obs['observation_id']}")
            self.assertIn(obs["encounter_id"], encounter_ids, f"Orphan observation encounter: {obs['observation_id']}")

        # Check medications foreign keys
        for med in self.medications:
            self.assertIn(med["patient_id"], patient_ids, f"Orphan medication patient: {med['medication_id']}")
            self.assertIn(med["encounter_id"], encounter_ids, f"Orphan medication encounter: {med['medication_id']}")

        # Check risk assessments foreign keys
        for rsk in self.risk_assessments:
            self.assertIn(rsk["patient_id"], patient_ids, f"Orphan risk assessment: {rsk['assessment_id']}")

    # 2. Validate Realistic Clinical Chronology
    def test_chronological_consistency(self):
        patient_dob = {p["patient_id"]: datetime.strptime(p["birth_date"], "%Y-%m-%d") for p in self.patients}
        patient_reg = {p["patient_id"]: datetime.strptime(p["registered_date"], "%Y-%m-%d") for p in self.patients}
        encounter_dates = {e["encounter_id"]: datetime.strptime(e["encounter_date"], "%Y-%m-%d") for e in self.encounters}

        # Condition onset must not precede birth
        for cond in self.conditions:
            p_dob = patient_dob[cond["patient_id"]]
            onset_dt = datetime.strptime(cond["onset_date"], "%Y-%m-%d")
            self.assertGreaterEqual(
                onset_dt, p_dob,
                f"Condition {cond['condition_id']} onset {onset_dt} before birth {p_dob}"
            )

        # Encounter date must be >= registration date
        for enc in self.encounters:
            p_reg = patient_reg[enc["patient_id"]]
            enc_dt = encounter_dates[enc["encounter_id"]]
            self.assertGreaterEqual(
                enc_dt, p_reg,
                f"Encounter {enc['encounter_id']} date {enc_dt} before clinic registration {p_reg}"
            )

        # Observation date must equal encounter date
        for obs in self.observations:
            enc_dt = encounter_dates[obs["encounter_id"]].strftime("%Y-%m-%d")
            self.assertEqual(
                obs["date"], enc_dt,
                f"Observation date {obs['date']} does not match encounter date {enc_dt}"
            )

        # Medication start date must equal encounter date and medication end date >= start date
        for med in self.medications:
            enc_dt = encounter_dates[med["encounter_id"]].strftime("%Y-%m-%d")
            self.assertEqual(
                med["start_date"], enc_dt,
                f"Medication start {med['start_date']} does not match encounter date {enc_dt}"
            )
            start_dt = datetime.strptime(med["start_date"], "%Y-%m-%d")
            end_dt = datetime.strptime(med["end_date"], "%Y-%m-%d")
            self.assertGreaterEqual(end_dt, start_dt, "Medication end date cannot be before start date")

    # 3. Verify ICD-10 and LOINC Mappings, Clinical Units and Reference Ranges
    def test_clinical_coding_standards(self):
        valid_icd10 = {"E11.9", "I10", "J44.9", "A15.0", "A90", "I25.10", "E78.5", "K21.9", "N18.3"}
        for cond in self.conditions:
            self.assertIn(
                cond["diagnosis_code"], valid_icd10,
                f"Invalid ICD-10 code {cond['diagnosis_code']}"
            )

        valid_loinc = {
            "8480-6": {"unit": "mmHg", "ref": "90-120"},
            "8462-4": {"unit": "mmHg", "ref": "60-80"},
            "1558-6": {"unit": "mg/dL", "ref": "70-99"},
            "4548-4": {"unit": "%", "ref": "<5.7"},
            "59408-5": {"unit": "%", "ref": "95-100"}
        }
        for obs in self.observations:
            code = obs["test_code"]
            self.assertIn(code, valid_loinc, f"Unexpected LOINC code {code}")
            self.assertEqual(obs["unit"], valid_loinc[code]["unit"], f"Unit mismatch for {code}")
            self.assertEqual(obs["reference_range"], valid_loinc[code]["ref"], f"Reference range mismatch for {code}")
            self.assertIn(obs["interpretation"], ["Normal", "High", "Low"])
            # Numerical validation
            val = float(obs["value_numeric"])
            self.assertGreater(val, 0)

    # 4. Check Medication-to-Condition Consistency
    def test_medication_condition_indication_consistency(self):
        patient_conditions = {}
        for c in self.conditions:
            patient_conditions.setdefault(c["patient_id"], set()).add(c["diagnosis_code"])

        for med in self.medications:
            p_id = med["patient_id"]
            indicated_code = med["indication_condition_code"]
            self.assertIn(
                indicated_code, patient_conditions.get(p_id, set()),
                f"Patient {p_id} prescribed {med['medication_name']} without diagnosed indication {indicated_code}"
            )

    # 5. Verify Internal Synthetic Identifiers
    def test_internal_synthetic_id_formatting(self):
        for p in self.patients:
            mock_id = p["abha_number"]
            self.assertTrue(
                mock_id.startswith("SYNTH-ID-"),
                f"Identifier {mock_id} should use internal synthetic prefix SYNTH-ID-"
            )

    # 6. Verify Cardiovascular Risk Score Model is Documented as Heuristic Simulation
    def test_cvd_risk_model_documentation_and_bounds(self):
        for rsk in self.risk_assessments:
            self.assertEqual(rsk["model_type"], "SIMULATED_HEURISTIC")
            self.assertIn("SIMULATED_HEURISTIC_WHO_ISH", rsk["model_version"])
            self.assertIn("not clinically validated", rsk["model_documentation"].lower())
            score = float(rsk["score"])
            self.assertTrue(0.0 <= score <= 1.0, f"Score out of bounds: {score}")
            self.assertIn(rsk["risk_category"], ["Low (<10%)", "Moderate (10-19%)", "High (20-29%)", "Very High (>=30%)"])

    # 7. Clearly Label All Patient Records, Facilities and Risk Scores as Synthetic
    def test_synthetic_labels_across_all_tables(self):
        for p in self.patients:
            self.assertEqual(p["is_synthetic"], "TRUE")
            self.assertEqual(p["data_source"], "SYNTHETIC_SIMULATION")
        for enc in self.encounters:
            self.assertEqual(enc["is_synthetic"], "TRUE")
            self.assertTrue(enc["facility"].endswith("[SYNTHETIC]"), f"Facility not flagged synthetic: {enc['facility']}")
        for cond in self.conditions:
            self.assertEqual(cond["is_synthetic"], "TRUE")
        for obs in self.observations:
            self.assertEqual(obs["is_synthetic"], "TRUE")
        for med in self.medications:
            self.assertEqual(med["is_synthetic"], "TRUE")
        for rsk in self.risk_assessments:
            self.assertEqual(rsk["is_synthetic"], "TRUE")
        for aud in self.audit_logs:
            self.assertEqual(aud["is_synthetic"], "TRUE")

        self.assertTrue(self.manifest["is_synthetic"])

if __name__ == "__main__":
    unittest.main()
