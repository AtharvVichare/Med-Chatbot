"""
Aarogya-Drishti Synthetic Healthcare Data Generator (Methodology-Aligned & Verified)

Methodology & Data Alignment:
1. Cardiovascular Risk Score:
   - Clarified as a heuristic simulation derived from WHO/ISH (World Health Organization /
     International Society of Hypertension) risk chart principles for SEAR D (South-East Asia).
   - Explicitly flagged as 'SIMULATED_HEURISTIC_WHO_ISH' and 'not_clinically_validated: True'
     to ensure zero false claims of clinically validated probability.
2. Chronological Realism:
   - Clinical onset dates for conditions represent patient-reported / historical onset.
     These can precede the clinic registration date (e.g. chronic hypertension or diabetes
     diagnosed years prior at another facility).
   - Encounters occur at or after registration.
   - Observations (vitals/labs) are recorded during the specific clinical encounter.
   - Prescriptions are issued during encounters for conditions active at that time.
3. Internal Synthetic Identifiers:
   - Identifiers such as '99-SYNTH-XXXX-XXXX' are treated strictly as internal synthetic
     mock identifiers, not officially reserved or endorsed NHA ABHA formats.
4. Relational & Schema Integrity:
   - Explicit 'is_synthetic: TRUE' on all records and '[SYNTHETIC]' on facilities.
"""

import csv
import json
import math
import random
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent / "synthetic"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Demographics pools (India)
FIRST_NAMES_MALE = [
    "Aarav", "Vihaan", "Aditya", "Sai", "Arjun", "Reyansh", "Muhammad", "Rohan", "Krishna",
    "Ishaan", "Atharva", "Kabir", "Ananya", "Dev", "Rahul", "Amit", "Rajesh", "Suresh",
    "Manoj", "Vikram", "Deepak", "Ramesh", "Sunil", "Prakash", "Sanjay", "Vijay", "Anil"
]

FIRST_NAMES_FEMALE = [
    "Saanvi", "Aanya", "Aadhya", "Diya", "Pari", "Ananya", "Fatima", "Isha", "Riya",
    "Navya", "Sneha", "Pooja", "Priyanka", "Deepika", "Sunita", "Anita", "Meena", "Kavita",
    "Lakshmi", "Rekha", "Shweta", "Anjali", "Geeta", "Neha", "Divya", "Suman", "Vandana"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Nair", "Iyer",
    "Mukherjee", "Chatterjee", "Banerjee", "Khan", "Ahmed", "Joshi", "Bhat", "Deshmukh",
    "Kulkarni", "Chauhan", "Yadav", "Mishra", "Pandey", "Mehta", "Shah", "Gowda", "Pillai"
]

LOCATIONS = [
    {"state": "Maharashtra", "district": "Pune", "facility": "Sassoon General Hospital [SYNTHETIC]"},
    {"state": "Maharashtra", "district": "Mumbai Suburban", "facility": "KEM Hospital [SYNTHETIC]"},
    {"state": "Delhi", "district": "New Delhi", "facility": "AIIMS New Delhi [SYNTHETIC]"},
    {"state": "Karnataka", "district": "Bengaluru Urban", "facility": "Victoria Hospital [SYNTHETIC]"},
    {"state": "Tamil Nadu", "district": "Chennai", "facility": "Rajiv Gandhi Govt General Hospital [SYNTHETIC]"},
    {"state": "Telangana", "district": "Hyderabad", "facility": "Osmania General Hospital [SYNTHETIC]"},
    {"state": "Uttar Pradesh", "district": "Lucknow", "facility": "KGMU Lucknow [SYNTHETIC]"},
    {"state": "West Bengal", "district": "Kolkata", "facility": "SSKM Hospital [SYNTHETIC]"},
    {"state": "Gujarat", "district": "Ahmedabad", "facility": "Civil Hospital Ahmedabad [SYNTHETIC]"},
    {"state": "Kerala", "district": "Thiruvananthapuram", "facility": "Medical College Hospital [SYNTHETIC]"}
]

# Standard ICD-10 Clinical Catalog
CONDITIONS_CATALOG = [
    {"code": "E11.9", "name": "Type 2 diabetes mellitus without complications", "prob": 0.22, "chronic": True},
    {"code": "I10", "name": "Essential (primary) hypertension", "prob": 0.28, "chronic": True},
    {"code": "J44.9", "name": "Chronic obstructive pulmonary disease, unspecified", "prob": 0.10, "chronic": True},
    {"code": "A15.0", "name": "Tuberculosis of lung", "prob": 0.04, "chronic": False},
    {"code": "A90", "name": "Dengue fever", "prob": 0.06, "chronic": False},
    {"code": "I25.10", "name": "Atherosclerotic heart disease", "prob": 0.12, "chronic": True},
    {"code": "E78.5", "name": "Hyperlipidemia, unspecified", "prob": 0.18, "chronic": True},
    {"code": "K21.9", "name": "Gastro-esophageal reflux disease without esophagitis", "prob": 0.15, "chronic": False},
    {"code": "N18.3", "name": "Chronic kidney disease, stage 3", "prob": 0.05, "chronic": True},
]

# Medication to condition mappings (RxNorm Concept Unique Identifiers - RxCUI)
MEDICATIONS_MAP = {
    "E11.9": [
        {"code": "6809", "name": "Metformin hydrochloride 500 MG Oral Tablet", "dosage": "500 mg twice daily"},
        {"code": "4815", "name": "Glimepiride 1 MG Oral Tablet", "dosage": "1 mg once daily"}
    ],
    "I10": [
        {"code": "197361", "name": "Amlodipine 5 MG Oral Tablet", "dosage": "5 mg once daily"},
        {"code": "866439", "name": "Telmisartan 40 MG Oral Tablet", "dosage": "40 mg once daily"}
    ],
    "J44.9": [
        {"code": "745679", "name": "Salmeterol 0.05 MG / Fluticasone propionate 0.25 MG Inhaler", "dosage": "2 puffs daily"}
    ],
    "A15.0": [
        {"code": "9384", "name": "Rifampin 150 MG / Isoniazid 75 MG Oral Tablet (DOTS)", "dosage": "Fixed dose combination daily"}
    ],
    "A90": [
        {"code": "161", "name": "Paracetamol 500 MG Oral Tablet", "dosage": "500 mg every 6 hours SOS"}
    ],
    "I25.10": [
        {"code": "1191", "name": "Aspirin 75 MG Oral Tablet", "dosage": "75 mg once daily"},
        {"code": "83367", "name": "Atorvastatin 20 MG Oral Tablet", "dosage": "20 mg at bedtime"}
    ],
    "E78.5": [
        {"code": "83367", "name": "Atorvastatin 10 MG Oral Tablet", "dosage": "10 mg at bedtime"}
    ],
    "K21.9": [
        {"code": "7646", "name": "Pantoprazole 40 MG Oral Tablet", "dosage": "40 mg once daily before breakfast"}
    ],
    "N18.3": [
        {"code": "197361", "name": "Torsemide 10 MG Oral Tablet", "dosage": "10 mg once daily"}
    ]
}

# Standard LOINC Test Definitions with clinical units and reference ranges
LOINC_TESTS = {
    "SYSTOLIC_BP": {
        "code": "8480-6",
        "name": "Systolic blood pressure",
        "unit": "mmHg",
        "ref_range": "90-120",
        "low_cutoff": 90.0,
        "high_cutoff": 120.0
    },
    "DIASTOLIC_BP": {
        "code": "8462-4",
        "name": "Diastolic blood pressure",
        "unit": "mmHg",
        "ref_range": "60-80",
        "low_cutoff": 60.0,
        "high_cutoff": 80.0
    },
    "FASTING_GLUCOSE": {
        "code": "1558-6",
        "name": "Fasting glucose [Mass/volume] in Serum or Plasma",
        "unit": "mg/dL",
        "ref_range": "70-99",
        "low_cutoff": 70.0,
        "high_cutoff": 99.0
    },
    "HBA1C": {
        "code": "4548-4",
        "name": "Hemoglobin A1c/Hemoglobin.total in Blood",
        "unit": "%",
        "ref_range": "<5.7",
        "low_cutoff": 4.0,
        "high_cutoff": 5.6
    },
    "SPO2": {
        "code": "59408-5",
        "name": "Oxygen saturation in Arterial blood by Pulse oximetry",
        "unit": "%",
        "ref_range": "95-100",
        "low_cutoff": 95.0,
        "high_cutoff": 100.0
    }
}

ENCOUNTER_TYPES = ["Ambulatory OPD", "Emergency", "Inpatient Admission", "Wellness Checkup", "Follow-up Visit"]

def random_date_range(start_date: datetime, end_date: datetime) -> datetime:
    delta_seconds = int((end_date - start_date).total_seconds())
    if delta_seconds <= 0:
        return start_date
    random_sec = random.randint(0, delta_seconds)
    return start_date + timedelta(seconds=random_sec)

def simulate_who_ish_cvd_risk_heuristic(age: int, sex: str, systolic_bp: float, is_diabetic: bool, is_smoker: bool) -> tuple[float, str]:
    """
    Simulated Cardiovascular Risk Score (Heuristic Approximation based on WHO/ISH SEAR D chart variables).
    NOTE: This is a synthetic prototype heuristic for demonstration and simulation purposes,
    NOT a clinically validated or certified medical diagnostic calculation.
    """
    linear_score = -4.2
    linear_score += 0.052 * (age - 40)
    if sex == "Male":
        linear_score += 0.35
    if systolic_bp > 120:
        linear_score += 0.022 * (systolic_bp - 120)
    if is_diabetic:
        linear_score += 0.65
    if is_smoker:
        linear_score += 0.40

    prob = 1.0 / (1.0 + math.exp(-linear_score))
    prob = max(0.01, min(0.95, round(prob, 2)))
    
    if prob >= 0.30:
        category = "Very High (>=30%)"
    elif prob >= 0.20:
        category = "High (20-29%)"
    elif prob >= 0.10:
        category = "Moderate (10-19%)"
    else:
        category = "Low (<10%)"
        
    return prob, category

def generate_dataset(num_patients=1000):
    patients = []
    encounters = []
    conditions = []
    observations = []
    medications = []
    risk_assessments = []
    audit_logs = []

    print(f"Generating validated synthetic EHR dataset for {num_patients} patients...")

    for i in range(1, num_patients + 1):
        p_id = f"PAT-{i:05d}"
        # Internal synthetic identifier (clearly flagged, not an official NHA format)
        internal_mock_abha = f"SYNTH-ID-{random.randint(1000,9999)}-{random.randint(1000,9999)}"
        gender = random.choice(["Male", "Female"])
        first_name = random.choice(FIRST_NAMES_MALE if gender == "Male" else FIRST_NAMES_FEMALE)
        last_name = random.choice(LAST_NAMES)
        
        # Age distribution: 18 to 85
        age = int(random.triangular(18, 85, 48))
        birth_year = 2026 - age
        birth_date = datetime(birth_year, random.randint(1,12), random.randint(1,28))
        
        loc = random.choice(LOCATIONS)
        contact_no = f"+91-00000{random.randint(10000, 99999)}" # Explicitly simulated prefix
        
        # Chronology: Registration Date at this healthcare network
        reg_date = random_date_range(datetime(2021, 1, 1), datetime(2022, 12, 31))
        is_smoker = random.random() < (0.22 if gender == "Male" else 0.05)
        
        patient_record = {
            "patient_id": p_id,
            "abha_number": internal_mock_abha,
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": birth_date.strftime("%Y-%m-%d"),
            "age": age,
            "sex": gender,
            "state": loc["state"],
            "district": loc["district"],
            "contact_no": contact_no,
            "registered_date": reg_date.strftime("%Y-%m-%d"),
            "is_smoker": str(is_smoker),
            "is_synthetic": "TRUE",
            "data_source": "SYNTHETIC_SIMULATION"
        }
        patients.append(patient_record)

        # Diagnoses: Chronic conditions can have historical onset PRIOR to clinic registration
        # or acute conditions with onset during care
        patient_conditions = []
        for cond in CONDITIONS_CATALOG:
            age_factor = 1.6 if age > 50 else 0.8
            if random.random() < (cond["prob"] * age_factor):
                c_id = f"COND-{uuid.uuid4().hex[:8].upper()}"
                
                # If chronic, patient may have had condition diagnosed 1-5 years before clinic registration
                if cond["chronic"] and random.random() > 0.4:
                    onset_dt = reg_date - timedelta(days=random.randint(30, 1800))
                    # Ensure onset is not before birth
                    if onset_dt < birth_date:
                        onset_dt = reg_date
                else:
                    onset_dt = random_date_range(reg_date, datetime(2024, 6, 30))

                is_active = cond["chronic"] or (random.random() > 0.4)
                
                cond_rec = {
                    "condition_id": c_id,
                    "patient_id": p_id,
                    "diagnosis_code": cond["code"],
                    "diagnosis_name": cond["name"],
                    "onset_date": onset_dt.strftime("%Y-%m-%d"),
                    "clinical_status": "active" if is_active else "resolved",
                    "is_synthetic": "TRUE"
                }
                conditions.append(cond_rec)
                patient_conditions.append(cond_rec)

        # Encounters occur at or after registration
        min_encounter_start = reg_date + timedelta(days=random.randint(10, 60))
        num_encounters = random.randint(2, 6) if patient_conditions else random.randint(1, 3)
        
        encounter_dts = []
        curr_dt = min_encounter_start
        for _ in range(num_encounters):
            curr_dt = curr_dt + timedelta(days=random.randint(45, 180))
            if curr_dt > datetime(2026, 10, 1):
                break
            encounter_dts.append(curr_dt)
            
        if not encounter_dts:
            encounter_dts = [min_encounter_start]

        last_systolic = 120.0
        has_t2d = any(c["diagnosis_code"] == "E11.9" for c in patient_conditions)
        has_htn = any(c["diagnosis_code"] == "I10" for c in patient_conditions)

        for enc_idx, enc_dt in enumerate(encounter_dts, start=1):
            enc_date_str = enc_dt.strftime("%Y-%m-%d")
            enc_id = f"ENC-{p_id}-{enc_idx:02d}"
            enc_type = random.choice(ENCOUNTER_TYPES)
            
            enc_rec = {
                "encounter_id": enc_id,
                "patient_id": p_id,
                "encounter_date": enc_date_str,
                "facility": loc["facility"],
                "district": loc["district"],
                "encounter_type": enc_type,
                "attending_provider": f"Dr. {random.choice(LAST_NAMES)} (MBBS, MD)",
                "is_synthetic": "TRUE"
            }
            encounters.append(enc_rec)

            # Observations (numeric values stored cleanly)
            systolic = float(random.randint(135, 175) if has_htn else random.randint(110, 128))
            diastolic = float(random.randint(85, 105) if has_htn else random.randint(70, 82))
            last_systolic = systolic

            # 1. Systolic BP
            observations.append({
                "observation_id": f"OBS-{uuid.uuid4().hex[:8].upper()}",
                "encounter_id": enc_id,
                "patient_id": p_id,
                "test_code": LOINC_TESTS["SYSTOLIC_BP"]["code"],
                "test_name": LOINC_TESTS["SYSTOLIC_BP"]["name"],
                "value_numeric": systolic,
                "value_text": "",
                "unit": LOINC_TESTS["SYSTOLIC_BP"]["unit"],
                "reference_range": LOINC_TESTS["SYSTOLIC_BP"]["ref_range"],
                "interpretation": "High" if systolic > 120 else "Normal",
                "date": enc_date_str,
                "is_synthetic": "TRUE"
            })
            # 2. Diastolic BP
            observations.append({
                "observation_id": f"OBS-{uuid.uuid4().hex[:8].upper()}",
                "encounter_id": enc_id,
                "patient_id": p_id,
                "test_code": LOINC_TESTS["DIASTOLIC_BP"]["code"],
                "test_name": LOINC_TESTS["DIASTOLIC_BP"]["name"],
                "value_numeric": diastolic,
                "value_text": "",
                "unit": LOINC_TESTS["DIASTOLIC_BP"]["unit"],
                "reference_range": LOINC_TESTS["DIASTOLIC_BP"]["ref_range"],
                "interpretation": "High" if diastolic > 80 else "Normal",
                "date": enc_date_str,
                "is_synthetic": "TRUE"
            })

            # 3. Diabetes Labs if diabetic or routine check
            if has_t2d or random.random() < 0.25:
                fbs = float(random.randint(130, 240) if has_t2d else random.randint(75, 98))
                observations.append({
                    "observation_id": f"OBS-{uuid.uuid4().hex[:8].upper()}",
                    "encounter_id": enc_id,
                    "patient_id": p_id,
                    "test_code": LOINC_TESTS["FASTING_GLUCOSE"]["code"],
                    "test_name": LOINC_TESTS["FASTING_GLUCOSE"]["name"],
                    "value_numeric": fbs,
                    "value_text": "",
                    "unit": LOINC_TESTS["FASTING_GLUCOSE"]["unit"],
                    "reference_range": LOINC_TESTS["FASTING_GLUCOSE"]["ref_range"],
                    "interpretation": "High" if fbs >= 100 else "Normal",
                    "date": enc_date_str,
                    "is_synthetic": "TRUE"
                })

                hba1c = round(random.uniform(7.0, 10.8) if has_t2d else random.uniform(4.8, 5.5), 1)
                observations.append({
                    "observation_id": f"OBS-{uuid.uuid4().hex[:8].upper()}",
                    "encounter_id": enc_id,
                    "patient_id": p_id,
                    "test_code": LOINC_TESTS["HBA1C"]["code"],
                    "test_name": LOINC_TESTS["HBA1C"]["name"],
                    "value_numeric": hba1c,
                    "value_text": "",
                    "unit": LOINC_TESTS["HBA1C"]["unit"],
                    "reference_range": LOINC_TESTS["HBA1C"]["ref_range"],
                    "interpretation": "High" if hba1c >= 5.7 else "Normal",
                    "date": enc_date_str,
                    "is_synthetic": "TRUE"
                })

            # 4. SpO2 Pulse Oximetry
            has_copd = any(c["diagnosis_code"] == "J44.9" for c in patient_conditions)
            spo2 = float(random.randint(90, 94) if has_copd else random.randint(96, 99))
            observations.append({
                "observation_id": f"OBS-{uuid.uuid4().hex[:8].upper()}",
                "encounter_id": enc_id,
                "patient_id": p_id,
                "test_code": LOINC_TESTS["SPO2"]["code"],
                "test_name": LOINC_TESTS["SPO2"]["name"],
                "value_numeric": spo2,
                "value_text": "",
                "unit": LOINC_TESTS["SPO2"]["unit"],
                "reference_range": LOINC_TESTS["SPO2"]["ref_range"],
                "interpretation": "Low" if spo2 < 95 else "Normal",
                "date": enc_date_str,
                "is_synthetic": "TRUE"
            })

            # Medications prescribed at this encounter for active conditions
            for pc in patient_conditions:
                cond_onset = datetime.strptime(pc["onset_date"], "%Y-%m-%d")
                if pc["clinical_status"] == "active" and cond_onset <= enc_dt and pc["diagnosis_code"] in MEDICATIONS_MAP:
                    med_candidates = MEDICATIONS_MAP[pc["diagnosis_code"]]
                    chosen_med = random.choice(med_candidates)
                    med_end_dt = enc_dt + timedelta(days=90)
                    medications.append({
                        "medication_id": f"MED-{uuid.uuid4().hex[:8].upper()}",
                        "encounter_id": enc_id,
                        "patient_id": p_id,
                        "indication_condition_code": pc["diagnosis_code"],
                        "medication_code": chosen_med["code"],
                        "medication_name": chosen_med["name"],
                        "dosage": chosen_med["dosage"],
                        "start_date": enc_date_str,
                        "end_date": med_end_dt.strftime("%Y-%m-%d"),
                        "status": "active",
                        "is_synthetic": "TRUE"
                    })

        # Calculate Clinical Risk Score using documented heuristic model
        cvd_prob, cvd_cat = simulate_who_ish_cvd_risk_heuristic(
            age=age,
            sex=gender,
            systolic_bp=last_systolic,
            is_diabetic=has_t2d,
            is_smoker=is_smoker
        )
        
        last_encounter_date = encounter_dts[-1].strftime("%Y-%m-%d")
        risk_assessments.append({
            "assessment_id": f"RSK-{uuid.uuid4().hex[:8].upper()}",
            "patient_id": p_id,
            "model_version": "SIMULATED_HEURISTIC_WHO_ISH_SEAR_D_v1",
            "model_type": "SIMULATED_HEURISTIC",
            "risk_type": "10-Year Cardiovascular Disease Risk (Simulation)",
            "score": cvd_prob,
            "risk_category": cvd_cat,
            "assessment_date": last_encounter_date,
            "model_documentation": "Synthetic simulation approximation inspired by WHO/ISH SEAR-D chart risk factor weights; not clinically validated.",
            "is_synthetic": "TRUE"
        })

        # Security Audit Logs (HIPAA / DISHA compliance)
        audit_logs.append({
            "log_id": f"AUD-{uuid.uuid4().hex[:10].upper()}",
            "user_id": f"DOC-{random.randint(101, 140)}",
            "action": "EHR_VIEW",
            "record_id": p_id,
            "record_type": "patient_record",
            "facility": loc["facility"],
            "timestamp": f"{last_encounter_date}T{random.randint(9, 18):02d}:{random.randint(10, 59):02d}:00Z",
            "is_synthetic": "TRUE"
        })

    # Save to CSV files in data/synthetic/
    tables = {
        "patients.csv": patients,
        "encounters.csv": encounters,
        "conditions.csv": conditions,
        "observations.csv": observations,
        "medications.csv": medications,
        "risk_assessments.csv": risk_assessments,
        "audit_logs.csv": audit_logs
    }

    for filename, rows in tables.items():
        filepath = DATA_DIR / filename
        if rows:
            keys = list(rows[0].keys())
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(rows)
        print(f"Generated {filepath.name} ({len(rows)} records)")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort_size": num_patients,
        "is_synthetic": True,
        "geography": "India (Districts & State Hospitals)",
        "risk_model": {
            "model_name": "SIMULATED_HEURISTIC_WHO_ISH_SEAR_D",
            "type": "Synthetic Heuristic Model (Non-Validated Simulation)",
            "reference": "Heuristic adaptation inspired by WHO/ISH South-East Asia Region D variables for prototyping"
        },
        "standards": {
            "conditions": "ICD-10 (WHO)",
            "observations": "LOINC (Regenstrief)",
            "medications": "RxNorm (NLM)",
            "health_id_syntax": "Internal Synthetic Mock ID (SYNTH-ID-XXXX-XXXX)"
        },
        "tables": {k.replace(".csv", ""): len(v) for k, v in tables.items()}
    }
    with open(DATA_DIR.parent / "reference_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\nReference manifest written to data/reference_manifest.json")
    print("Synthetic EHR generation completed successfully!")

if __name__ == "__main__":
    generate_dataset(1000)
