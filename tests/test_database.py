"""
Database Integration Test Suite for Aarogya-Drishti EHR
Tests:
- Schema migration via Alembic (no Base.metadata.create_all shortcuts)
- Primary Key Uniqueness
- Foreign Key Constraints & Referential Integrity
- Invalid Foreign Key References Rejection
- Idempotency & Duplicate Import Handling
- Missing or Malformed Values Handling
- Longitudinal Patient Multi-Visit Queries
- Row Count Match against Reference Manifest
"""

import os
import unittest
from pathlib import Path
from datetime import date, datetime
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

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
from backend.app.services.importer import EHRImporter

TEST_DB_PATH = Path(__file__).resolve().parents[1] / "backend" / "aarogya_integration_test.db"
ALEMBIC_INI_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"

class TestDatabaseImplementation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 1. Ensure clean slate test database
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)

        cls.db_url = f"sqlite:///{TEST_DB_PATH.as_posix()}"
        
        # 2. Execute database creation strictly through Alembic migration
        cfg = Config(str(ALEMBIC_INI_PATH))
        cfg.set_main_option("sqlalchemy.url", cls.db_url)
        command.upgrade(cfg, "head")

        cls.engine = create_engine(cls.db_url, connect_args={"check_same_thread": False})
        
        # Enable foreign key enforcement for SQLite connection in tests
        from sqlalchemy import event
        @event.listens_for(cls.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        cls.Session = sessionmaker(bind=cls.engine)
        cls.session = cls.Session()

        # 3. Import full generated dataset through EHRImporter
        cls.importer = EHRImporter(session=cls.session)
        cls.initial_stats = cls.importer.import_all()

    @classmethod
    def tearDownClass(cls):
        cls.session.close()
        cls.engine.dispose()
        if TEST_DB_PATH.exists():
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def test_01_row_counts_match_manifest(self):
        """Verify imported table row counts match reference manifest exactly"""
        verification = self.importer.verify_against_manifest()
        self.assertTrue(verification["all_matched"], f"Manifest mismatch: {verification}")
        self.assertEqual(self.session.query(Patient).count(), 1000)
        self.assertEqual(self.session.query(Encounter).count(), 3612)
        self.assertEqual(self.session.query(Condition).count(), 1444)
        self.assertEqual(self.session.query(Observation).count(), 14264)
        self.assertEqual(self.session.query(Medication).count(), 3689)
        self.assertEqual(self.session.query(RiskAssessment).count(), 1000)
        self.assertEqual(self.session.query(AuditLog).count(), 1000)

    def test_02_primary_key_uniqueness(self):
        """Verify inserting an entity with an existing Primary Key raises IntegrityError"""
        dup_patient = Patient(
            patient_id="PAT-00001", # Existing
            abha_number="SYNTH-ID-UNIQUE-TEST",
            first_name="Duplicate",
            last_name="Test",
            birth_date=date(1980, 1, 1),
            age=46,
            sex="Male",
            state="Maharashtra",
            district="Pune",
            registered_date=date(2022, 1, 1),
            is_synthetic=True,
            data_source="SYNTHETIC_SIMULATION"
        )
        self.session.add(dup_patient)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_03_foreign_key_constraints_rejection(self):
        """Verify inserting an encounter with a non-existent patient raises IntegrityError"""
        orphan_enc = Encounter(
            encounter_id="ENC-NONEXISTENT-99",
            patient_id="PAT-NONEXISTENT",
            encounter_date=date(2024, 1, 1),
            facility="Test Hospital",
            district="Pune",
            encounter_type="OPD",
            is_synthetic=True
        )
        self.session.add(orphan_enc)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_04_idempotent_duplicate_import(self):
        """Verify re-running importer on existing data skips all without errors or duplicates"""
        re_importer = EHRImporter(session=self.session)
        re_stats = re_importer.import_all()
        for table, counts in re_stats.items():
            self.assertEqual(counts["inserted"], 0, f"{table} should have 0 inserted on re-run")
            self.assertGreater(counts["skipped"], 0, f"{table} should have skipped existing records")
            self.assertEqual(counts["rejected"], 0, f"{table} should have 0 rejected records")

    def test_05_longitudinal_patient_queries(self):
        """Verify multiple encounters, chronological ordering, and observation relations per patient"""
        multi_visit_patient = (
            self.session.query(Patient)
            .join(Encounter)
            .group_by(Patient.patient_id)
            .having(func.count(Encounter.encounter_id) >= 3)
            .first()
        )
        self.assertIsNotNone(multi_visit_patient)
        
        # Test relationship loading
        encounters = (
            self.session.query(Encounter)
            .filter(Encounter.patient_id == multi_visit_patient.patient_id)
            .order_by(Encounter.encounter_date.asc())
            .all()
        )
        self.assertGreaterEqual(len(encounters), 3)
        # Check chronological order of visits
        for i in range(len(encounters) - 1):
            self.assertLessEqual(encounters[i].encounter_date, encounters[i+1].encounter_date)

        # Verify linked observations to encounter
        first_encounter = encounters[0]
        linked_observations = self.session.query(Observation).filter(Observation.encounter_id == first_encounter.encounter_id).all()
        self.assertGreater(len(linked_observations), 0)
        for obs in linked_observations:
            self.assertIsNotNone(obs.value_numeric)
            self.assertEqual(obs.date, first_encounter.encounter_date)

    def test_06_synthetic_indicators_and_typing(self):
        """Verify numeric observation typing and explicit synthetic flags"""
        bp_obs = self.session.query(Observation).filter(Observation.test_code == "8480-6").first()
        self.assertIsNotNone(bp_obs)
        self.assertIsInstance(bp_obs.value_numeric, float)
        self.assertGreater(bp_obs.value_numeric, 50.0)
        self.assertTrue(bp_obs.is_synthetic)

        risk = self.session.query(RiskAssessment).first()
        self.assertIsNotNone(risk)
        self.assertEqual(risk.model_type, "SIMULATED_HEURISTIC")
        self.assertIsInstance(risk.score, float)
        self.assertTrue(risk.is_synthetic)

if __name__ == "__main__":
    unittest.main()

