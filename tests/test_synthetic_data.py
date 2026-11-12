"""
Unit Test Suite for Synthetic Longitudinal EHR Data
Built with standard library unittest (no external packages required).
"""

import csv
import json
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

class TestSyntheticEHRData(unittest.TestCase):

    def test_manifest_exists_and_accurate(self):
        manifest_file = DATA_DIR / "reference_manifest.json"
        self.assertTrue(manifest_file.exists(), "Manifest file missing")
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["cohort_size"], 1000)
        self.assertEqual(manifest["tables"]["patients"], 1000)

    def test_patients_table(self):
        patients = load_csv("patients.csv")
        self.assertEqual(len(patients), 1000)
        p = patients[0]
        required_cols = {"patient_id", "abha_number", "birth_date", "age", "sex", "district", "state"}
        self.assertTrue(required_cols.issubset(p.keys()))
        self.assertTrue(p["patient_id"].startswith("PAT-"))
        self.assertIn(p["sex"], ["Male", "Female"])

    def test_longitudinal_encounters(self):
        patients = load_csv("patients.csv")
        encounters = load_csv("encounters.csv")
        patient_ids = {p["patient_id"] for p in patients}
        
        # Longitudinality check: multiple encounters
        self.assertGreater(len(encounters), len(patients), "Encounters must exceed patient count for longitudinal data")

        for enc in encounters[:500]:
            self.assertIn(enc["patient_id"], patient_ids)
            self.assertTrue(len(enc["encounter_type"]) > 0)
            self.assertTrue(len(enc["facility"]) > 0)

        # Confirm multi-visit distribution
        patient_visit_counts = {}
        for enc in encounters:
            patient_visit_counts[enc["patient_id"]] = patient_visit_counts.get(enc["patient_id"], 0) + 1
        
        multi_visit_count = sum(1 for count in patient_visit_counts.values() if count > 1)
        self.assertGreater(multi_visit_count, 500, "Cohort must contain multiple visits per patient")

    def test_observations(self):
        observations = load_csv("observations.csv")
        patients = load_csv("patients.csv")
        patient_ids = {p["patient_id"] for p in patients}
        
        self.assertGreater(len(observations), 5000)
        for obs in observations[:500]:
            self.assertIn(obs["patient_id"], patient_ids)
            self.assertTrue(len(obs["test_code"]) > 0)
            # Observations store typed numeric or text measurements
            val_num = obs.get("value_numeric")
            val_text = obs.get("value_text")
            self.assertTrue(val_num is not None or val_text is not None)
            self.assertTrue(len(obs["unit"]) > 0)

    def test_conditions_and_medications(self):
        conditions = load_csv("conditions.csv")
        medications = load_csv("medications.csv")
        self.assertGreater(len(conditions), 0)
        self.assertGreater(len(medications), 0)
        
        icd_codes = {c["diagnosis_code"] for c in conditions}
        self.assertTrue("E11.9" in icd_codes or "I10" in icd_codes)

    def test_audit_logs(self):
        audit_logs = load_csv("audit_logs.csv")
        self.assertGreaterEqual(len(audit_logs), 1000)
        for log_entry in audit_logs[:100]:
            self.assertIn("user_id", log_entry)
            self.assertIn("action", log_entry)
            self.assertIn("timestamp", log_entry)

if __name__ == "__main__":
    unittest.main()
