"""
CSV Data Importer for Aarogya-Drishti EHR
Imports generated synthetic datasets into database (PostgreSQL / SQLite) with:
- Strict relational order (Patients -> Conditions -> Encounters -> Observations/Medications -> Risk Assessments -> Audit Logs)
- Pydantic schema validation per row
- Atomic transactions with rollback on failure
- Idempotency (skips existing records without duplicates)
- Inserted, skipped, rejected metric reporting
- Comparison against reference_manifest.json
"""

import csv
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import SessionLocal, get_engine
from backend.app.db.models import (
    Base,
    Patient,
    Encounter,
    Condition,
    Observation,
    Medication,
    RiskAssessment,
    AuditLog
)
from backend.app.db.schemas import (
    PatientBase,
    EncounterBase,
    ConditionBase,
    ObservationBase,
    MedicationBase,
    RiskAssessmentBase,
    AuditLogBase
)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
MANIFEST_PATH = DATA_DIR / "reference_manifest.json"

def parse_date(date_str: str) -> Optional[date]:
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def parse_datetime(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)

class EHRImporter:

    def __init__(self, session: Session = None, engine = None):
        self.session = session or SessionLocal()
        self.engine = engine or self.session.get_bind()
        self.stats = {
            "patients": {"inserted": 0, "skipped": 0, "rejected": 0},
            "conditions": {"inserted": 0, "skipped": 0, "rejected": 0},
            "encounters": {"inserted": 0, "skipped": 0, "rejected": 0},
            "observations": {"inserted": 0, "skipped": 0, "rejected": 0},
            "medications": {"inserted": 0, "skipped": 0, "rejected": 0},
            "risk_assessments": {"inserted": 0, "skipped": 0, "rejected": 0},
            "audit_logs": {"inserted": 0, "skipped": 0, "rejected": 0},
        }

    def import_patients(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_ids = set(self.session.scalars(select(Patient.patient_id)).all())
            to_insert = []
            
            for row in reader:
                p_id = row["patient_id"]
                if p_id in existing_ids:
                    self.stats["patients"]["skipped"] += 1
                    continue
                try:
                    validated = PatientBase(
                        patient_id=p_id,
                        abha_number=row["abha_number"],
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        birth_date=parse_date(row["birth_date"]),
                        age=int(row["age"]),
                        sex=row["sex"],
                        state=row["state"],
                        district=row["district"],
                        contact_no=row.get("contact_no"),
                        registered_date=parse_date(row["registered_date"]),
                        is_smoker=row.get("is_smoker", "").lower() == "true",
                        is_synthetic=row.get("is_synthetic", "").upper() == "TRUE",
                        data_source=row.get("data_source", "SYNTHETIC_SIMULATION")
                    )
                    obj = Patient(**validated.model_dump())
                    to_insert.append(obj)
                    existing_ids.add(p_id)
                except Exception:
                    self.stats["patients"]["rejected"] += 1

            if to_insert:
                self.session.add_all(to_insert)
                self.session.flush()
                self.stats["patients"]["inserted"] += len(to_insert)

    def import_conditions(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_ids = set(self.session.scalars(select(Condition.condition_id)).all())
            patient_ids = set(self.session.scalars(select(Patient.patient_id)).all())
            to_insert = []
            
            for row in reader:
                c_id = row["condition_id"]
                p_id = row["patient_id"]
                if c_id in existing_ids:
                    self.stats["conditions"]["skipped"] += 1
                    continue
                if p_id not in patient_ids:
                    self.stats["conditions"]["rejected"] += 1
                    continue
                try:
                    validated = ConditionBase(
                        condition_id=c_id,
                        patient_id=p_id,
                        diagnosis_code=row["diagnosis_code"],
                        diagnosis_name=row["diagnosis_name"],
                        onset_date=parse_date(row["onset_date"]),
                        clinical_status=row.get("clinical_status", "active"),
                        is_synthetic=row.get("is_synthetic", "").upper() == "TRUE"
                    )
                    to_insert.append(Condition(**validated.model_dump()))
                    existing_ids.add(c_id)
                except Exception:
                    self.stats["conditions"]["rejected"] += 1

            if to_insert:
                self.session.add_all(to_insert)
                self.session.flush()
                self.stats["conditions"]["inserted"] += len(to_insert)

    def import_encounters(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_ids = set(self.session.scalars(select(Encounter.encounter_id)).all())
            patient_ids = set(self.session.scalars(select(Patient.patient_id)).all())
            to_insert = []
            
            for row in reader:
                e_id = row["encounter_id"]
                p_id = row["patient_id"]
                if e_id in existing_ids:
                    self.stats["encounters"]["skipped"] += 1
                    continue
                if p_id not in patient_ids:
                    self.stats["encounters"]["rejected"] += 1
                    continue
                try:
                    validated = EncounterBase(
                        encounter_id=e_id,
                        patient_id=p_id,
                        encounter_date=parse_date(row["encounter_date"]),
                        facility=row["facility"],
                        district=row["district"],
                        encounter_type=row["encounter_type"],
                        attending_provider=row.get("attending_provider"),
                        is_synthetic=row.get("is_synthetic", "").upper() == "TRUE"
                    )
                    to_insert.append(Encounter(**validated.model_dump()))
                    existing_ids.add(e_id)
                except Exception:
                    self.stats["encounters"]["rejected"] += 1

            if to_insert:
                self.session.add_all(to_insert)
                self.session.flush()
                self.stats["encounters"]["inserted"] += len(to_insert)

    def import_observations(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_ids = set(self.session.scalars(select(Observation.observation_id)).all())
            encounter_ids = set(self.session.scalars(select(Encounter.encounter_id)).all())
            patient_ids = set(self.session.scalars(select(Patient.patient_id)).all())
            to_insert = []
            
            for row in reader:
                obs_id = row["observation_id"]
                enc_id = row["encounter_id"]
                p_id = row["patient_id"]
                if obs_id in existing_ids:
                    self.stats["observations"]["skipped"] += 1
                    continue
                if enc_id not in encounter_ids or p_id not in patient_ids:
                    self.stats["observations"]["rejected"] += 1
                    continue
                try:
                    num_val = float(row["value_numeric"]) if row.get("value_numeric") else None
                    validated = ObservationBase(
                        observation_id=obs_id,
                        encounter_id=enc_id,
                        patient_id=p_id,
                        test_code=row["test_code"],
                        test_name=row["test_name"],
                        value_numeric=num_val,
                        value_text=row.get("value_text") or None,
                        unit=row.get("unit"),
                        reference_range=row.get("reference_range"),
                        interpretation=row.get("interpretation"),
                        date=parse_date(row["date"]),
                        is_synthetic=row.get("is_synthetic", "").upper() == "TRUE"
                    )
                    to_insert.append(Observation(**validated.model_dump()))
                    existing_ids.add(obs_id)
                except Exception:
                    self.stats["observations"]["rejected"] += 1

            if to_insert:
                self.session.add_all(to_insert)
                self.session.flush()
                self.stats["observations"]["inserted"] += len(to_insert)

    def import_medications(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_ids = set(self.session.scalars(select(Medication.medication_id)).all())
            encounter_ids = set(self.session.scalars(select(Encounter.encounter_id)).all())
            patient_ids = set(self.session.scalars(select(Patient.patient_id)).all())
            to_insert = []
            
            for row in reader:
                med_id = row["medication_id"]
                enc_id = row["encounter_id"]
                p_id = row["patient_id"]
                if med_id in existing_ids:
                    self.stats["medications"]["skipped"] += 1
                    continue
                if enc_id not in encounter_ids or p_id not in patient_ids:
                    self.stats["medications"]["rejected"] += 1
                    continue
                try:
                    validated = MedicationBase(
                        medication_id=med_id,
                        encounter_id=enc_id,
                        patient_id=p_id,
                        indication_condition_code=row.get("indication_condition_code"),
                        medication_code=row["medication_code"],
                        medication_name=row["medication_name"],
                        dosage=row["dosage"],
                        start_date=parse_date(row["start_date"]),
                        end_date=parse_date(row.get("end_date")),
                        status=row.get("status", "active"),
                        is_synthetic=row.get("is_synthetic", "").upper() == "TRUE"
                    )
                    to_insert.append(Medication(**validated.model_dump()))
                    existing_ids.add(med_id)
                except Exception:
                    self.stats["medications"]["rejected"] += 1

            if to_insert:
                self.session.add_all(to_insert)
                self.session.flush()
                self.stats["medications"]["inserted"] += len(to_insert)

    def import_risk_assessments(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_ids = set(self.session.scalars(select(RiskAssessment.assessment_id)).all())
            patient_ids = set(self.session.scalars(select(Patient.patient_id)).all())
            to_insert = []
            
            for row in reader:
                rsk_id = row["assessment_id"]
                p_id = row["patient_id"]
                if rsk_id in existing_ids:
                    self.stats["risk_assessments"]["skipped"] += 1
                    continue
                if p_id not in patient_ids:
                    self.stats["risk_assessments"]["rejected"] += 1
                    continue
                try:
                    validated = RiskAssessmentBase(
                        assessment_id=rsk_id,
                        patient_id=p_id,
                        model_version=row["model_version"],
                        model_type=row.get("model_type", "SIMULATED_HEURISTIC"),
                        risk_type=row["risk_type"],
                        score=float(row["score"]),
                        risk_category=row["risk_category"],
                        assessment_date=parse_date(row["assessment_date"]),
                        model_documentation=row.get("model_documentation"),
                        is_synthetic=row.get("is_synthetic", "").upper() == "TRUE"
                    )
                    to_insert.append(RiskAssessment(**validated.model_dump()))
                    existing_ids.add(rsk_id)
                except Exception:
                    self.stats["risk_assessments"]["rejected"] += 1

            if to_insert:
                self.session.add_all(to_insert)
                self.session.flush()
                self.stats["risk_assessments"]["inserted"] += len(to_insert)

    def import_audit_logs(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_ids = set(self.session.scalars(select(AuditLog.log_id)).all())
            to_insert = []
            
            for row in reader:
                log_id = row["log_id"]
                if log_id in existing_ids:
                    self.stats["audit_logs"]["skipped"] += 1
                    continue
                try:
                    validated = AuditLogBase(
                        log_id=log_id,
                        user_id=row["user_id"],
                        action=row["action"],
                        record_id=row["record_id"],
                        record_type=row["record_type"],
                        facility=row.get("facility"),
                        timestamp=parse_datetime(row["timestamp"]),
                        is_synthetic=row.get("is_synthetic", "").upper() == "TRUE"
                    )
                    to_insert.append(AuditLog(**validated.model_dump()))
                    existing_ids.add(log_id)
                except Exception:
                    self.stats["audit_logs"]["rejected"] += 1

            if to_insert:
                self.session.add_all(to_insert)
                self.session.flush()
                self.stats["audit_logs"]["inserted"] += len(to_insert)

    def import_all(self, data_directory: Path = SYNTHETIC_DIR) -> Dict[str, Any]:
        """Execute atomic full import with transaction management"""
        try:
            print("Beginning atomic relational EHR import...")
            self.import_patients(data_directory / "patients.csv")
            self.import_conditions(data_directory / "conditions.csv")
            self.import_encounters(data_directory / "encounters.csv")
            self.import_observations(data_directory / "observations.csv")
            self.import_medications(data_directory / "medications.csv")
            self.import_risk_assessments(data_directory / "risk_assessments.csv")
            self.import_audit_logs(data_directory / "audit_logs.csv")
            
            self.session.commit()
            print("Import committed successfully.")
            return self.stats
        except Exception as e:
            self.session.rollback()
            print(f"Error during import: {e}. Rolled back transaction.")
            raise e

    def verify_against_manifest(self) -> Dict[str, Any]:
        if not MANIFEST_PATH.exists():
            return {"error": "Manifest file missing"}
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        expected = manifest.get("tables", {})
        actual = {
            "patients": self.session.query(Patient).count(),
            "encounters": self.session.query(Encounter).count(),
            "conditions": self.session.query(Condition).count(),
            "observations": self.session.query(Observation).count(),
            "medications": self.session.query(Medication).count(),
            "risk_assessments": self.session.query(RiskAssessment).count(),
            "audit_logs": self.session.query(AuditLog).count()
        }
        comparison = {}
        for table, exp_count in expected.items():
            act_count = actual.get(table, 0)
            comparison[table] = {
                "expected": exp_count,
                "actual": act_count,
                "match": exp_count == act_count
            }
        return {"comparison": comparison, "all_matched": all(v["match"] for v in comparison.values())}

if __name__ == "__main__":
    importer = EHRImporter()
    stats = importer.import_all()
    print("Import Stats:", json.dumps(stats, indent=2))
    manifest_check = importer.verify_against_manifest()
    print("Manifest Verification:", json.dumps(manifest_check, indent=2))
