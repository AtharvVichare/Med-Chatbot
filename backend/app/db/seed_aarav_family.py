import json
import uuid
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal, engine
from backend.app.db.models import (
    Base,
    Patient,
    UserAccount,
    Encounter,
    Condition,
    Observation,
    Medication,
    Allergy,
    FamilyMember,
    FamilyCondition,
    DailyHealthLog,
    PatientDocument,
    AppointmentBooking,
    AdmissionRequest,
    BedRegistry,
    ClinicalNote,
    ClinicalOrder,
    NursingTask,
    MedicationAdministration,
    ShiftHandover,
    FamilyLink,
    CareTeamAssignment,
    DoctorProfile
)
from backend.app.core.security import hash_password

DEMO_PASSWORD = "DemoPassword123!"


def seed_demo_family_accounts():
    db: Session = SessionLocal()
    print("=" * 80)
    print("SEEDING AARAV MEHTA DEMO FAMILY ACCOUNTS & COMPLETE LONGITUDINAL EHR")
    print("=" * 80)

    try:
        # Ensure all tables exist
        Base.metadata.create_all(bind=engine)

        # 1. Create Patient Demographics
        demo_patients_data = [
            {
                "patient_id": "PAT-AARAV-001",
                "abha_number": "14-1234-5678-9001",
                "first_name": "Aarav",
                "last_name": "Mehta",
                "birth_date": date(1988, 5, 14),
                "age": 38,
                "sex": "male",
                "state": "Maharashtra",
                "district": "Mumbai",
                "contact_no": "9820112345",
                "registered_date": date(2023, 1, 10),
                "is_smoker": False,
                "is_synthetic": True,
                "data_source": "SYNTHETIC_DEMO_FAMILY"
            },
            {
                "patient_id": "PAT-PRIYA-002",
                "abha_number": "14-1234-5678-9002",
                "first_name": "Priya",
                "last_name": "Mehta",
                "birth_date": date(1990, 8, 22),
                "age": 36,
                "sex": "female",
                "state": "Maharashtra",
                "district": "Mumbai",
                "contact_no": "9820112346",
                "registered_date": date(2023, 2, 15),
                "is_smoker": False,
                "is_synthetic": True,
                "data_source": "SYNTHETIC_DEMO_FAMILY"
            },
            {
                "patient_id": "PAT-ROHAN-003",
                "abha_number": "14-1234-5678-9003",
                "first_name": "Rohan",
                "last_name": "Mehta",
                "birth_date": date(1992, 11, 30),
                "age": 34,
                "sex": "male",
                "state": "Maharashtra",
                "district": "Mumbai",
                "contact_no": "9820112347",
                "registered_date": date(2023, 3, 20),
                "is_smoker": False,
                "is_synthetic": True,
                "data_source": "SYNTHETIC_DEMO_FAMILY"
            },
            {
                "patient_id": "PAT-SUNITA-004",
                "abha_number": "14-1234-5678-9004",
                "first_name": "Sunita",
                "last_name": "Mehta",
                "birth_date": date(1962, 3, 18),
                "age": 64,
                "sex": "female",
                "state": "Maharashtra",
                "district": "Mumbai",
                "contact_no": "9820112348",
                "registered_date": date(2022, 6, 12),
                "is_smoker": False,
                "is_synthetic": True,
                "data_source": "SYNTHETIC_DEMO_FAMILY"
            }
        ]

        for p_data in demo_patients_data:
            existing = db.query(Patient).filter(Patient.patient_id == p_data["patient_id"]).first()
            if not existing:
                p = Patient(**p_data)
                db.add(p)
                print(f"Created Patient: {p_data['first_name']} {p_data['last_name']} ({p_data['patient_id']})")
            else:
                for k, v in p_data.items():
                    setattr(existing, k, v)
        db.commit()

        # 2. Create User Accounts in users table
        demo_users_data = [
            {"username": "aarav_mehta", "email": "aarav.mehta@demo-aarogya.in", "full_name": "Aarav Mehta", "patient_id": "PAT-AARAV-001", "role": "patient", "gender": "male", "dob": date(1988, 5, 14), "phone": "9820112345"},
            {"username": "priya_mehta", "email": "priya.mehta@demo-aarogya.in", "full_name": "Priya Mehta", "patient_id": "PAT-PRIYA-002", "role": "patient", "gender": "female", "dob": date(1990, 8, 22), "phone": "9820112346"},
            {"username": "rohan_mehta", "email": "rohan.mehta@demo-aarogya.in", "full_name": "Rohan Mehta", "patient_id": "PAT-ROHAN-003", "role": "patient", "gender": "male", "dob": date(1992, 11, 30), "phone": "9820112347"},
            {"username": "sunita_mehta", "email": "sunita.mehta@demo-aarogya.in", "full_name": "Sunita Mehta", "patient_id": "PAT-SUNITA-004", "role": "patient", "gender": "female", "dob": date(1962, 3, 18), "phone": "9820112348"},
            {"username": "nurse_user", "email": "nurse.anjali@kem-hospital.edu.in", "full_name": "Nurse Anjali Sharma", "patient_id": None, "role": "nurse", "gender": "female", "dob": date(1985, 4, 10), "phone": "9820199999"}
        ]

        pwd_hash = hash_password(DEMO_PASSWORD)
        for u_data in demo_users_data:
            existing_user = db.query(UserAccount).filter(UserAccount.username == u_data["username"]).first()
            if not existing_user:
                u = UserAccount(
                    id=f"USR-{uuid.uuid4().hex[:10].upper()}",
                    email=u_data["email"],
                    username=u_data["username"],
                    password_hash=pwd_hash,
                    full_name=u_data["full_name"],
                    role=u_data["role"],
                    patient_id=u_data["patient_id"],
                    phone_number=u_data["phone"],
                    date_of_birth=u_data["dob"],
                    gender=u_data["gender"],
                    is_active=True,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(u)
                print(f"Created UserAccount: {u_data['username']} ({u_data['role']})")
        db.commit()

        # 3. Create Pre-Linked Verified Family Connections
        all_perms = [
            "view_basic_health",
            "view_medical_history",
            "view_reports",
            "manage_appointments",
            "receive_reminders",
            "assist_admissions",
            "access_documents"
        ]
        brother_perms = [
            "view_basic_health",
            "manage_appointments",
            "receive_reminders"
        ]

        family_links_data = [
            # Aarav <-> Priya (Spouse)
            {
                "link_id": "FLK-AARAV-PRIYA",
                "requester_patient_id": "PAT-AARAV-001",
                "target_patient_id": "PAT-PRIYA-002",
                "relationship_type": "spouse",
                "status": "approved",
                "permissions_json": json.dumps(all_perms),
                "notes": "Spousal full proxy consent granted"
            },
            # Aarav <-> Sunita (Mother)
            {
                "link_id": "FLK-AARAV-SUNITA",
                "requester_patient_id": "PAT-AARAV-001",
                "target_patient_id": "PAT-SUNITA-004",
                "relationship_type": "child",
                "status": "approved",
                "permissions_json": json.dumps(all_perms),
                "notes": "Maternal caregiving & clinical proxy access"
            },
            # Aarav <-> Rohan (Brother)
            {
                "link_id": "FLK-AARAV-ROHAN",
                "requester_patient_id": "PAT-AARAV-001",
                "target_patient_id": "PAT-ROHAN-003",
                "relationship_type": "sibling",
                "status": "approved",
                "permissions_json": json.dumps(brother_perms),
                "notes": "Sibling emergency & appointment coordination"
            }
        ]

        for fl in family_links_data:
            existing = db.query(FamilyLink).filter(FamilyLink.link_id == fl["link_id"]).first()
            if not existing:
                link = FamilyLink(
                    link_id=fl["link_id"],
                    requester_patient_id=fl["requester_patient_id"],
                    target_patient_id=fl["target_patient_id"],
                    relationship_type=fl["relationship_type"],
                    status=fl["status"],
                    permissions_json=fl["permissions_json"],
                    requested_at=datetime.now(timezone.utc) - timedelta(days=60),
                    responded_at=datetime.now(timezone.utc) - timedelta(days=59),
                    notes=fl["notes"]
                )
                db.add(link)
                print(f"Created FamilyLink: {fl['link_id']} ({fl['relationship_type']})")
        db.commit()

        # 4. Seed Encounters for Aarav Mehta
        encounters_data = [
            {
                "encounter_id": "ENC-AARAV-001",
                "patient_id": "PAT-AARAV-001",
                "encounter_date": date(2026, 8, 15),
                "facility": "Seth GS Medical College & KEM Hospital, Mumbai",
                "district": "Mumbai",
                "encounter_type": "inpatient",
                "attending_provider": "Dr. Priya Deshmukh, MD (Cardiology & Internal Medicine)",
                "assigned_bed": "BED-DLX-01",
                "encounter_status": "discharged"
            },
            {
                "encounter_id": "ENC-AARAV-002",
                "patient_id": "PAT-AARAV-001",
                "encounter_date": date(2026, 10, 10),
                "facility": "Lilavati Hospital & Research Centre, Mumbai",
                "district": "Mumbai",
                "encounter_type": "ambulatory",
                "attending_provider": "Dr. Rajesh Sharma, MD (Pulmonology)",
                "assigned_bed": None,
                "encounter_status": "completed"
            },
            {
                "encounter_id": "ENC-AARAV-003",
                "patient_id": "PAT-AARAV-001",
                "encounter_date": date(2026, 11, 5),
                "facility": "P.D. Hinduja National Hospital, Mumbai",
                "district": "Mumbai",
                "encounter_type": "ambulatory",
                "attending_provider": "Dr. Priya Deshmukh, MD (Cardiology & Internal Medicine)",
                "assigned_bed": None,
                "encounter_status": "completed"
            }
        ]

        for enc in encounters_data:
            existing = db.query(Encounter).filter(Encounter.encounter_id == enc["encounter_id"]).first()
            if not existing:
                db.add(Encounter(
                    encounter_id=enc["encounter_id"],
                    patient_id=enc["patient_id"],
                    encounter_date=enc["encounter_date"],
                    facility=enc["facility"],
                    district=enc["district"],
                    encounter_type=enc["encounter_type"],
                    attending_provider=enc["attending_provider"],
                    assigned_bed=enc["assigned_bed"],
                    encounter_status=enc["encounter_status"],
                    is_synthetic=True,
                    created_at=datetime.combine(enc["encounter_date"], datetime.min.time())
                ))
        db.commit()

        # 5. Seed Conditions for Aarav Mehta
        conditions_data = [
            {
                "condition_id": "CND-AARAV-001",
                "patient_id": "PAT-AARAV-001",
                "diagnosis_code": "J45.909",
                "diagnosis_name": "Bronchial Asthma (Moderate Persistent)",
                "onset_date": date(2021, 4, 10),
                "clinical_status": "active"
            },
            {
                "condition_id": "CND-AARAV-002",
                "patient_id": "PAT-AARAV-001",
                "diagnosis_code": "I10",
                "diagnosis_name": "Essential (Primary) Hypertension",
                "onset_date": date(2024, 1, 15),
                "clinical_status": "active"
            },
            {
                "condition_id": "CND-AARAV-003",
                "patient_id": "PAT-AARAV-001",
                "diagnosis_code": "J45.0",
                "diagnosis_name": "Allergic Rhinitis with Seasonal Exacerbation",
                "onset_date": date(2022, 9, 5),
                "clinical_status": "active"
            }
        ]

        for cnd in conditions_data:
            existing = db.query(Condition).filter(Condition.condition_id == cnd["condition_id"]).first()
            if not existing:
                db.add(Condition(
                    condition_id=cnd["condition_id"],
                    patient_id=cnd["patient_id"],
                    diagnosis_code=cnd["diagnosis_code"],
                    diagnosis_name=cnd["diagnosis_name"],
                    onset_date=cnd["onset_date"],
                    clinical_status=cnd["clinical_status"],
                    is_synthetic=True,
                    created_at=datetime.combine(cnd["onset_date"], datetime.min.time())
                ))
        db.commit()

        # 6. Seed Prescriptions/Medications for Aarav Mehta
        medications_data = [
            {
                "medication_id": "MED-AARAV-001",
                "encounter_id": "ENC-AARAV-001",
                "patient_id": "PAT-AARAV-001",
                "indication_condition_code": "J45.909",
                "medication_code": "RX-BUD-FORM-200",
                "medication_name": "Budesonide/Formoterol 200/6mcg DPI Inhaler",
                "dosage": "2 puffs twice daily (BID)",
                "start_date": date(2026, 8, 18),
                "status": "active"
            },
            {
                "medication_id": "MED-AARAV-002",
                "encounter_id": "ENC-AARAV-001",
                "patient_id": "PAT-AARAV-001",
                "indication_condition_code": "J45.909",
                "medication_code": "RX-MONT-10",
                "medication_name": "Montelukast Sodium 10mg",
                "dosage": "1 tablet orally at bedtime (QHS)",
                "start_date": date(2026, 8, 18),
                "status": "active"
            },
            {
                "medication_id": "MED-AARAV-003",
                "encounter_id": "ENC-AARAV-003",
                "patient_id": "PAT-AARAV-001",
                "indication_condition_code": "I10",
                "medication_code": "RX-AMLO-5",
                "medication_name": "Amlodipine Besylate 5mg",
                "dosage": "1 tablet orally once daily in the morning (QD)",
                "start_date": date(2026, 11, 5),
                "status": "active"
            }
        ]

        for med in medications_data:
            existing = db.query(Medication).filter(Medication.medication_id == med["medication_id"]).first()
            if not existing:
                db.add(Medication(
                    medication_id=med["medication_id"],
                    encounter_id=med["encounter_id"],
                    patient_id=med["patient_id"],
                    indication_condition_code=med["indication_condition_code"],
                    medication_code=med["medication_code"],
                    medication_name=med["medication_name"],
                    dosage=med["dosage"],
                    start_date=med["start_date"],
                    status=med["status"],
                    is_synthetic=True,
                    created_at=datetime.combine(med["start_date"], datetime.min.time())
                ))
        db.commit()

        # 7. Seed Allergies for Aarav Mehta
        allergies_data = [
            {
                "allergy_id": "ALG-AARAV-001",
                "patient_id": "PAT-AARAV-001",
                "substance": "Penicillin (Amoxicillin, Ampicillin)",
                "reaction": "Anaphylaxis / Severe Generalized Urticaria",
                "severity": "severe",
                "category": "drug",
                "verification_status": "doctor_verified",
                "recorded_date": date(2019, 3, 10),
                "notes": "Developed severe bronchospasm and facial edema after Amoxicillin in 2019. Strict avoidance required."
            },
            {
                "allergy_id": "ALG-AARAV-002",
                "patient_id": "PAT-AARAV-001",
                "substance": "Aspirin & NSAIDs (Ibuprofen)",
                "reaction": "Aspirin-Exacerbated Respiratory Disease (AERD) / Wheezing",
                "severity": "moderate",
                "category": "drug",
                "verification_status": "doctor_verified",
                "recorded_date": date(2021, 6, 15),
                "notes": "Precipitates acute bronchospasm. Avoid all non-selective COX-1 inhibitors."
            }
        ]

        for alg in allergies_data:
            existing = db.query(Allergy).filter(Allergy.allergy_id == alg["allergy_id"]).first()
            if not existing:
                db.add(Allergy(
                    allergy_id=alg["allergy_id"],
                    patient_id=alg["patient_id"],
                    substance=alg["substance"],
                    reaction=alg["reaction"],
                    severity=alg["severity"],
                    category=alg["category"],
                    verification_status=alg["verification_status"],
                    recorded_date=alg["recorded_date"],
                    notes=alg["notes"],
                    created_at=datetime.combine(alg["recorded_date"], datetime.min.time())
                ))
        db.commit()

        # 8. Seed Lab Observations for Aarav Mehta
        observations_data = [
            {"test_code": "CBC-HGB", "test_name": "Hemoglobin", "value_numeric": 14.8, "unit": "g/dL", "reference_range": "13.5 - 17.5", "interpretation": "NORMAL", "date": date(2026, 8, 15)},
            {"test_code": "CBC-WBC", "test_name": "White Blood Cell Count (WBC)", "value_numeric": 7400.0, "unit": "/mcL", "reference_range": "4,000 - 11,000", "interpretation": "NORMAL", "date": date(2026, 8, 15)},
            {"test_code": "CBC-EOS", "test_name": "Absolute Eosinophil Count", "value_numeric": 480.0, "unit": "/mcL", "reference_range": "50 - 350", "interpretation": "HIGH", "date": date(2026, 8, 15)},
            {"test_code": "GLU-FAST", "test_name": "Fasting Plasma Glucose", "value_numeric": 92.0, "unit": "mg/dL", "reference_range": "70 - 99", "interpretation": "NORMAL", "date(2026, 11, 5)": date(2026, 11, 5)},
            {"test_code": "GLU-HBA1C", "test_name": "Glycated Hemoglobin (HbA1c)", "value_numeric": 5.4, "unit": "%", "reference_range": "4.0 - 5.6", "interpretation": "NORMAL", "date": date(2026, 11, 5)},
            {"test_code": "REN-CREAT", "test_name": "Serum Creatinine", "value_numeric": 0.88, "unit": "mg/dL", "reference_range": "0.70 - 1.30", "interpretation": "NORMAL", "date": date(2026, 11, 5)},
            {"test_code": "LIP-CHOL", "test_name": "Total Serum Cholesterol", "value_numeric": 196.0, "unit": "mg/dL", "reference_range": "< 200", "interpretation": "NORMAL", "date": date(2026, 11, 5)},
            {"test_code": "LIP-LDL", "test_name": "LDL Cholesterol", "value_numeric": 118.0, "unit": "mg/dL", "reference_range": "< 100", "interpretation": "BORDERLINE_HIGH", "date": date(2026, 11, 5)},
            {"test_code": "LIP-HDL", "test_name": "HDL Cholesterol", "value_numeric": 48.0, "unit": "mg/dL", "reference_range": "> 40", "interpretation": "NORMAL", "date": date(2026, 11, 5)},
            {"test_code": "PFT-FEV1", "test_name": "Spirometry FEV1 (% Predicted)", "value_numeric": 78.0, "unit": "%", "reference_range": ">= 80", "interpretation": "MILD_OBSTRUCTION", "date": date(2026, 10, 10)},
            {"test_code": "PFT-RATIO", "test_name": "FEV1 / FVC Ratio", "value_numeric": 71.0, "unit": "%", "reference_range": ">= 75", "interpretation": "MILD_OBSTRUCTION", "date": date(2026, 10, 10)}
        ]

        for obs in observations_data:
            obs_date = obs.get("date") or date(2026, 11, 5)
            obs_id = f"OBS-AARAV-{obs['test_code'].replace('-', '')}"
            existing = db.query(Observation).filter(Observation.observation_id == obs_id).first()
            if not existing:
                db.add(Observation(
                    observation_id=obs_id,
                    encounter_id="ENC-AARAV-001" if obs_date < date(2026, 9, 1) else ("ENC-AARAV-002" if obs_date < date(2026, 11, 1) else "ENC-AARAV-003"),
                    patient_id="PAT-AARAV-001",
                    test_code=obs["test_code"],
                    test_name=obs["test_name"],
                    value_numeric=obs["value_numeric"],
                    value_text=str(obs["value_numeric"]),
                    unit=obs["unit"],
                    reference_range=obs["reference_range"],
                    interpretation=obs["interpretation"],
                    date=obs_date,
                    is_synthetic=True,
                    created_at=datetime.combine(obs_date, datetime.min.time())
                ))
        db.commit()

        # 9. Seed Medical Imaging & Scans for Aarav Mehta
        documents_data = [
            {
                "document_id": "DOC-AARAV-CXR",
                "patient_id": "PAT-AARAV-001",
                "file_name": "Chest_XRay_PA_Aarav_Mehta.pdf",
                "file_type": "application/pdf",
                "file_path": "data/uploads/patient_documents/Aarav_Chest_XRay_PA.pdf",
                "file_size_bytes": 1048576,
                "document_type": "radiology_scan",
                "report_date": date(2026, 8, 15),
                "extracted_text": "DIGITAL CHEST RADIOGRAPH (PA VIEW)\nIndication: Acute exacerbation of bronchial asthma, dyspnea, wheezing.\nFindings: Lungs demonstrate bilateral hyperinflation with flattening of bilateral diaphragmatic domes, consistent with reactive airway bronchoconstriction. No focal parenchymal consolidation, cavitation, or pleural effusion. Cardiothoracic ratio is normal at 0.44. Bony thorax and soft tissues unremarkable.\nImpression: Bilateral pulmonary hyperinflation without acute pneumonia or pneumothorax.",
                "confirmation_status": "confirmed"
            },
            {
                "document_id": "DOC-AARAV-CT",
                "patient_id": "PAT-AARAV-001",
                "file_name": "High_Resolution_Chest_CT_Scan.pdf",
                "file_type": "application/pdf",
                "file_path": "data/uploads/patient_documents/Aarav_HRCT_Chest.pdf",
                "file_size_bytes": 2097152,
                "document_type": "radiology_scan",
                "report_date": date(2026, 8, 16),
                "extracted_text": "HIGH RESOLUTION COMPUTED TOMOGRAPHY (HRCT) OF THORAX\nTechnique: Volumetric thin-slice non-contrast scan.\nFindings: Mild bronchial wall thickening noted predominantly in bilateral lower lobes. Air-trapping noted on expiratory scans, compatible with small-airway disease in asthma. No evidence of bronchiectasis, interstitial fibrosis, or honeycombing. Trachea and central bronchi are patent. No mediastinal or hilar lymphadenopathy.\nImpression: Findings consistent with mild reactive airway disease with expiratory air-trapping. No structural parenchymal lung disease.",
                "confirmation_status": "confirmed"
            },
            {
                "document_id": "DOC-AARAV-MRI",
                "patient_id": "PAT-AARAV-001",
                "file_name": "Brain_MRI_Neuro_Screening.pdf",
                "file_type": "application/pdf",
                "file_path": "data/uploads/patient_documents/Aarav_Brain_MRI.pdf",
                "file_size_bytes": 3145728,
                "document_type": "radiology_scan",
                "report_date": date(2025, 6, 20),
                "extracted_text": "MAGNETIC RESONANCE IMAGING (MRI) OF THE BRAIN\nIndication: Evaluation of chronic tension headache.\nFindings: Multi-sequence multi-planar brain MRI reveals normal ventricular system and basal cisterns. Normal grey-white matter differentiation. No intra- or extra-axial mass, acute territorial infarction, hemorrhage, or midline shift. Major vascular flow voids are preserved. Paranasal sinuses demonstrate mild mucosal thickening in bilateral maxillary antra.\nImpression: Unremarkable non-contrast brain MRI. Incidental mild paranasal sinus mucosal thickening.",
                "confirmation_status": "confirmed"
            }
        ]

        for doc in documents_data:
            existing = db.query(PatientDocument).filter(PatientDocument.document_id == doc["document_id"]).first()
            if not existing:
                db.add(PatientDocument(
                    document_id=doc["document_id"],
                    patient_id=doc["patient_id"],
                    file_name=doc["file_name"],
                    file_type=doc["file_type"],
                    file_path=doc["file_path"],
                    file_size_bytes=doc["file_size_bytes"],
                    document_type=doc["document_type"],
                    report_date=doc["report_date"],
                    extracted_text=doc["extracted_text"],
                    confirmation_status=doc["confirmation_status"],
                    created_at=datetime.combine(doc["report_date"], datetime.min.time())
                ))
        db.commit()

        # 10. Seed Daily Longitudinal Tracking Vitals (last 30 days) for Aarav Mehta
        base_date = date.today()
        for i in range(30):
            d = base_date - timedelta(days=i)
            log_id = f"LOG-AARAV-{d.strftime('%Y%m%d')}"
            existing = db.query(DailyHealthLog).filter(DailyHealthLog.id == log_id).first()
            if not existing:
                # Realistic ambulatory readings
                systolic = 124.0 + (i % 6) * 2 - (i % 3)
                diastolic = 80.0 + (i % 4) * 2
                pulse = 72.0 + (i % 5) * 2
                spo2 = 97.0 + (1 if i % 2 == 0 else 0)
                glucose = 92.0 + (i % 5) * 2

                db.add(DailyHealthLog(
                    id=log_id,
                    patient_id="PAT-AARAV-001",
                    log_date=d,
                    systolic_bp=systolic,
                    diastolic_bp=diastolic,
                    pulse=pulse,
                    fasting_glucose=glucose,
                    weight_kg=74.5,
                    temperature_c=36.8,
                    spo2=spo2,
                    sleep_hours=7.5,
                    mood="Energetic & Stable",
                    steps_count=7800 + (i * 120) % 3000,
                    source="patient_home_monitor",
                    notes="Daily morning ambulatory check; inhaler taken as prescribed.",
                    created_at=datetime.combine(d, datetime.min.time())
                ))
        db.commit()

        # 11. Seed Clinical Notes for Aarav Mehta (from Physician)
        notes_data = [
            {
                "note_id": "NOTE-AARAV-001",
                "patient_id": "PAT-AARAV-001",
                "encounter_id": "ENC-AARAV-001",
                "doctor_id": "doctor_user",
                "doctor_name": "Dr. Priya Deshmukh",
                "note_type": "discharge_summary",
                "title": "Hospital Discharge Summary: Acute Bronchial Asthma Exacerbation",
                "subjective": "38yo male presented with severe acute bronchospasm, bilateral wheezing, and dyspnea. Admitted to Deluxe Ward Bed 01 for nebulization and parenteral therapy.",
                "objective": "Discharge Vitals: BP 122/80 mmHg, HR 74 bpm, SpO2 99% on room air, Afebrile. Chest auscultation clear bilaterally with no rhonchi or wheeze.",
                "assessment": "Acute Asthma Exacerbation - Resolved. Baseline moderate persistent asthma stabilized.",
                "plan": "1. Budesonide/Formoterol 200/6mcg Inhaler 2 puffs BID.\n2. Montelukast 10mg PO QHS.\n3. Avoid known triggers (cold air, dust, aspirin, penicillin).\n4. Follow up in Pulmonology OPD in 6-8 weeks.",
                "content": "Patient completed 3-day inpatient stay for asthma exacerbation. Responded well to inhaled bronchodilators and systemic corticosteroids. Discharged in stable condition."
            },
            {
                "note_id": "NOTE-AARAV-002",
                "patient_id": "PAT-AARAV-001",
                "encounter_id": "ENC-AARAV-003",
                "doctor_id": "doctor_user",
                "doctor_name": "Dr. Priya Deshmukh",
                "note_type": "consultation",
                "title": "Cardiovascular & Hypertension Follow-Up Consultation",
                "subjective": "Patient follows up for blood pressure review. Reports compliance with low-sodium DASH diet. Denies chest pain, orthopnea, or pedal edema.",
                "objective": "Clinic BP 126/82 mmHg. HR 72 bpm regular. Heart sounds S1, S2 present, no murmurs. Fasting Glucose 92 mg/dL, HbA1c 5.4%.",
                "assessment": "Stage 1 Essential Hypertension - Well controlled on Amlodipine 5mg monotherapy. ASCVD 10-year prospective risk is LOW.",
                "plan": "Continue Amlodipine 5mg QD. Maintain regular ambulatory BP log. Repeat lipid profile in 6 months.",
                "content": "Hypertension is currently well managed with low risk of cardiovascular progression. Discussed family history of paternal CAD."
            }
        ]

        for n in notes_data:
            existing = db.query(ClinicalNote).filter(ClinicalNote.note_id == n["note_id"]).first()
            if not existing:
                db.add(ClinicalNote(
                    note_id=n["note_id"],
                    patient_id=n["patient_id"],
                    encounter_id=n["encounter_id"],
                    doctor_id=n["doctor_id"],
                    doctor_name=n["doctor_name"],
                    note_type=n["note_type"],
                    title=n["title"],
                    subjective=n["subjective"],
                    objective=n["objective"],
                    assessment=n["assessment"],
                    plan=n["plan"],
                    content=n["content"],
                    created_at=datetime.now(timezone.utc) - timedelta(days=12),
                    updated_at=datetime.now(timezone.utc) - timedelta(days=12)
                ))
        db.commit()

        # 12. Seed Clinical Orders for Aarav Mehta
        orders_data = [
            {
                "order_id": "ORD-AARAV-001",
                "patient_id": "PAT-AARAV-001",
                "doctor_id": "doctor_user",
                "doctor_name": "Dr. Priya Deshmukh",
                "order_type": "lab",
                "order_name": "Lipid Profile & Serum Electrolytes Panel",
                "clinical_indication": "Annual cardiovascular preventive check and hypertension monitoring",
                "priority": "routine",
                "status": "completed",
                "result_summary": "Total Cholesterol 196 mg/dL, LDL 118 mg/dL, HDL 48 mg/dL. Normal renal electrolytes."
            },
            {
                "order_id": "ORD-AARAV-002",
                "patient_id": "PAT-AARAV-001",
                "doctor_id": "doctor_user",
                "doctor_name": "Dr. Priya Deshmukh",
                "order_type": "imaging",
                "order_name": "Chest X-Ray (PA View)",
                "clinical_indication": "Asthma baseline airway evaluation post-exacerbation",
                "priority": "routine",
                "status": "completed",
                "result_summary": "Bilateral hyperinflation without consolidation or effusion. Normal cardiac shadow."
            }
        ]

        for o in orders_data:
            existing = db.query(ClinicalOrder).filter(ClinicalOrder.order_id == o["order_id"]).first()
            if not existing:
                db.add(ClinicalOrder(
                    order_id=o["order_id"],
                    patient_id=o["patient_id"],
                    doctor_id=o["doctor_id"],
                    doctor_name=o["doctor_name"],
                    order_type=o["order_type"],
                    order_name=o["order_name"],
                    clinical_indication=o["clinical_indication"],
                    priority=o["priority"],
                    status=o["status"],
                    result_summary=o["result_summary"],
                    ordered_at=datetime.now(timezone.utc) - timedelta(days=14),
                    completed_at=datetime.now(timezone.utc) - timedelta(days=13)
                ))
        db.commit()

        # 13. Seed Medication Administrations (MAR) for Aarav Mehta & Ward Inpatients
        mar_data = [
            {
                "mar_id": "MAR-AARAV-001",
                "patient_id": "PAT-AARAV-001",
                "medication_id": "MED-AARAV-001",
                "medication_name": "Budesonide/Formoterol 200/6mcg Inhaler",
                "dosage": "2 puffs",
                "route": "inhalation",
                "scheduled_time": datetime.now(timezone.utc).replace(hour=8, minute=0, second=0),
                "administered_time": datetime.now(timezone.utc).replace(hour=8, minute=5, second=0),
                "administered_by": "Nurse Anjali Sharma",
                "status": "administered",
                "notes": "Patient self-administered with spacer under nursing supervision."
            },
            {
                "mar_id": "MAR-AARAV-002",
                "patient_id": "PAT-AARAV-001",
                "medication_id": "MED-AARAV-003",
                "medication_name": "Amlodipine Besylate 5mg",
                "dosage": "1 tab PO",
                "route": "oral",
                "scheduled_time": datetime.now(timezone.utc).replace(hour=9, minute=0, second=0),
                "administered_time": datetime.now(timezone.utc).replace(hour=9, minute=2, second=0),
                "administered_by": "Nurse Anjali Sharma",
                "status": "administered",
                "notes": "Pre-dose BP verified: 124/82 mmHg."
            },
            {
                "mar_id": "MAR-AARAV-003",
                "patient_id": "PAT-AARAV-001",
                "medication_id": "MED-AARAV-002",
                "medication_name": "Montelukast Sodium 10mg",
                "dosage": "1 tab PO",
                "route": "oral",
                "scheduled_time": datetime.now(timezone.utc).replace(hour=21, minute=0, second=0),
                "administered_time": None,
                "administered_by": None,
                "status": "scheduled",
                "notes": "Night dose pending bedside administration."
            }
        ]

        for m in mar_data:
            existing = db.query(MedicationAdministration).filter(MedicationAdministration.mar_id == m["mar_id"]).first()
            if not existing:
                db.add(MedicationAdministration(
                    mar_id=m["mar_id"],
                    patient_id=m["patient_id"],
                    medication_id=m["medication_id"],
                    medication_name=m["medication_name"],
                    dosage=m["dosage"],
                    route=m["route"],
                    scheduled_time=m["scheduled_time"],
                    administered_time=m["administered_time"],
                    administered_by=m["administered_by"],
                    status=m["status"],
                    notes=m["notes"],
                    created_at=datetime.now(timezone.utc)
                ))
        db.commit()

        # 14. Seed Nursing Tasks
        tasks_data = [
            {
                "task_id": "TSK-AARAV-001",
                "patient_id": "PAT-AARAV-001",
                "ward": "Deluxe Private Ward",
                "bed_number": "DELUXE-01",
                "task_type": "vitals",
                "title": "Evening Ambulatory Vitals Check & Peak Flow (PEFR)",
                "description": "Record BP, Heart Rate, SpO2, and peak expiratory flow rate using bedside meter.",
                "priority": "routine",
                "scheduled_time": datetime.now(timezone.utc) + timedelta(hours=2),
                "status": "pending",
                "assigned_nurse_id": "nurse_user",
                "assigned_nurse_name": "Nurse Anjali Sharma"
            },
            {
                "task_id": "TSK-AARAV-002",
                "patient_id": "PAT-AARAV-001",
                "ward": "Deluxe Private Ward",
                "bed_number": "DELUXE-01",
                "task_type": "medication",
                "title": "Bedtime Montelukast 10mg Administration",
                "description": "Verify patient identity, confirm absence of NSAID intake, administer 1 tab orally.",
                "priority": "routine",
                "scheduled_time": datetime.now(timezone.utc) + timedelta(hours=4),
                "status": "pending",
                "assigned_nurse_id": "nurse_user",
                "assigned_nurse_name": "Nurse Anjali Sharma"
            }
        ]

        for t in tasks_data:
            existing = db.query(NursingTask).filter(NursingTask.task_id == t["task_id"]).first()
            if not existing:
                db.add(NursingTask(
                    task_id=t["task_id"],
                    patient_id=t["patient_id"],
                    ward=t["ward"],
                    bed_number=t["bed_number"],
                    task_type=t["task_type"],
                    title=t["title"],
                    description=t["description"],
                    priority=t["priority"],
                    scheduled_time=t["scheduled_time"],
                    status=t["status"],
                    assigned_nurse_id=t["assigned_nurse_id"],
                    assigned_nurse_name=t["assigned_nurse_name"],
                    created_at=datetime.now(timezone.utc)
                ))
        db.commit()

        # 15. Seed SBAR Shift Handover Note
        existing_hnd = db.query(ShiftHandover).filter(ShiftHandover.ward == "Deluxe Private Ward").first()
        if not existing_hnd:
            db.add(ShiftHandover(
                handover_id="HND-DELUXE-001",
                ward="Deluxe Private Ward",
                shift_type="morning",
                outgoing_nurse_id="nurse_user",
                outgoing_nurse_name="Nurse Anjali Sharma",
                incoming_nurse_id="nurse_user",
                incoming_nurse_name="Nurse Kavita Joshi",
                handover_date=date.today(),
                situation="Ward at 85% occupancy with 12 admitted patients. Patient Aarav Mehta (Bed DELUXE-01) is stable post-asthma exacerbation.",
                background="Aarav Mehta, 38yo male, moderate persistent asthma & hypertension. Admitted for observation and bronchodilator optimization.",
                assessment="All vitals within normal parameters: BP 124/82 mmHg, HR 74 bpm, SpO2 98% room air. No wheezing on auscultation. Inhaler technique verified.",
                recommendation="Continue current therapy. Perform evening peak flow measurement at 18:00. Attending rounds scheduled with Dr. Priya Deshmukh at 16:30.",
                critical_alerts_json=json.dumps(["Penicillin and Aspirin allergy alert active for Aarav Mehta (Bed DELUXE-01)"]),
                total_patients=12,
                created_at=datetime.now(timezone.utc)
            ))
            db.commit()

        # 16. Seed Upcoming Appointment Booking for Aarav Mehta
        existing_appt = db.query(AppointmentBooking).filter(AppointmentBooking.patient_id == "PAT-AARAV-001").first()
        if not existing_appt:
            db.add(AppointmentBooking(
                booking_id="BKG-AARAV-001",
                patient_id="PAT-AARAV-001",
                doctor_id="DOC-CARD-001",
                department="Cardiology & Internal Medicine",
                hospital_name="Seth GS Medical College & KEM Hospital, Mumbai",
                booking_date=date.today() + timedelta(days=1),
                time_slot="10:00 AM",
                status="confirmed",
                chief_complaint="Routine quarterly hypertension & asthma maintenance follow-up",
                booked_via="intake_agent",
                created_at=datetime.now(timezone.utc)
            ))
            db.commit()

        # 17. Seed Family Pedigree History in FamilyMember & FamilyCondition tables
        existing_fm = db.query(FamilyMember).filter(FamilyMember.patient_id == "PAT-AARAV-001").all()
        if not existing_fm:
            # Mother: Sunita Mehta
            fm_mother = FamilyMember(
                id=f"FM-{uuid.uuid4().hex[:10].upper()}",
                patient_id="PAT-AARAV-001",
                relative_name="Sunita Mehta",
                relation_type="Mother",
                lineage="maternal",
                is_deceased=False,
                notes="Mother, 64yo, diagnosed with Type 2 Diabetes and Hypertension.",
                created_at=datetime.now(timezone.utc)
            )
            db.add(fm_mother)
            db.flush()

            db.add(FamilyCondition(
                id=f"FC-{uuid.uuid4().hex[:10].upper()}",
                family_member_id=fm_mother.id,
                condition_name="Type 2 Diabetes Mellitus",
                approximate_age_at_onset=52,
                notes="Controlled on Metformin"
            ))
            db.add(FamilyCondition(
                id=f"FC-{uuid.uuid4().hex[:10].upper()}",
                family_member_id=fm_mother.id,
                condition_name="Essential Hypertension",
                approximate_age_at_onset=50,
                notes="Controlled on Telmisartan"
            ))

            # Father: Late Ramesh Mehta
            fm_father = FamilyMember(
                id=f"FM-{uuid.uuid4().hex[:10].upper()}",
                patient_id="PAT-AARAV-001",
                relative_name="Late Ramesh Mehta",
                relation_type="Father",
                lineage="paternal",
                is_deceased=True,
                notes="Father, passed away at age 65 from Myocardial Infarction.",
                created_at=datetime.now(timezone.utc)
            )
            db.add(fm_father)
            db.flush()

            db.add(FamilyCondition(
                id=f"FC-{uuid.uuid4().hex[:10].upper()}",
                family_member_id=fm_father.id,
                condition_name="Coronary Artery Disease / Myocardial Infarction",
                approximate_age_at_onset=62,
                notes="CAD with acute STEMI"
            ))

            # Spouse: Priya Mehta
            fm_spouse = FamilyMember(
                id=f"FM-{uuid.uuid4().hex[:10].upper()}",
                patient_id="PAT-AARAV-001",
                relative_name="Priya Mehta",
                relation_type="Spouse",
                lineage="other",
                is_deceased=False,
                notes="Spouse, 36yo, active and healthy.",
                created_at=datetime.now(timezone.utc)
            )
            db.add(fm_spouse)

            db.commit()

        print("=" * 80)
        print("SUCCESSFULLY SEEDED ALL AARAV MEHTA DEMO FAMILY ACCOUNTS & COMPLETE EHR!")
        print("=" * 80)

    except Exception as e:
        db.rollback()
        print(f"Error seeding demo family accounts: {str(e)}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_family_accounts()
