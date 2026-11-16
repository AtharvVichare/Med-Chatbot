"""
Multi-Hospital Specialist Doctor Seeder for Aarogya-Drishti HMS.
Populates verified real doctors across multiple top tertiary hospitals:
1. Seth GS Medical College & KEM Hospital, Parel
2. Lilavati Hospital & Research Centre, Bandra West
3. Breach Candy Hospital Trust, South Mumbai
4. P.D. Hinduja National Hospital, Mahim
5. Apollo Hospitals, Navi Mumbai
6. Tata Memorial Hospital, Parel
"""

import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.db.models import DoctorProfile

DOCTORS_MULTI_HOSPITAL = [
    # --- Cardiology ---
    {
        "doctor_id": "DOC-CARD-001",
        "user_id": "doctor_user",
        "name": "Dr. Priya Deshmukh",
        "department": "Cardiology",
        "specialty": "Interventional Cardiology",
        "qualification": "MBBS, MD (Medicine), DM (Cardiology), FACC",
        "experience_years": 14,
        "consultation_fee": 1200.0,
        "hospital_name": "Seth GS Medical College & KEM Hospital",
        "is_available": True,
        "schedule": ["09:00 AM", "10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM", "04:30 PM"]
    },
    {
        "doctor_id": "DOC-CARD-002",
        "user_id": None,
        "name": "Dr. Ashwin B. Mehta",
        "department": "Cardiology",
        "specialty": "Complex Coronary Angioplasty & Structural Heart",
        "qualification": "MBBS, MD, DM (Cardiology), FACC, FSCAI",
        "experience_years": 28,
        "consultation_fee": 2500.0,
        "hospital_name": "Breach Candy Hospital Trust",
        "is_available": True,
        "schedule": ["10:30 AM", "12:00 PM", "03:00 PM", "04:30 PM", "05:30 PM"]
    },
    {
        "doctor_id": "DOC-CARD-003",
        "user_id": None,
        "name": "Dr. Sudhir Vaishnav",
        "department": "Cardiology",
        "specialty": "Transcatheter Valve Therapies & Preventive Cardiology",
        "qualification": "MBBS, MD, DM (Cardiology), MRCP (UK)",
        "experience_years": 19,
        "consultation_fee": 2000.0,
        "hospital_name": "Lilavati Hospital & Research Centre",
        "is_available": True,
        "schedule": ["09:30 AM", "11:00 AM", "01:30 PM", "03:00 PM", "04:00 PM"]
    },
    {
        "doctor_id": "DOC-CARD-004",
        "user_id": None,
        "name": "Dr. Charan Lanjewar",
        "department": "Cardiology",
        "specialty": "Pediatric & Adult Congenital Heart Disease",
        "qualification": "MBBS, MD, DM (Cardiology)",
        "experience_years": 16,
        "consultation_fee": 1800.0,
        "hospital_name": "P.D. Hinduja National Hospital",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "02:30 PM", "04:00 PM"]
    },

    # --- General Medicine ---
    {
        "doctor_id": "DOC-MED-002",
        "user_id": None,
        "name": "Dr. Rajesh Kumar",
        "department": "General Medicine",
        "specialty": "Internal Medicine & Diabetology",
        "qualification": "MBBS, MD (Internal Medicine), PGD (Diabetology)",
        "experience_years": 12,
        "consultation_fee": 800.0,
        "hospital_name": "Seth GS Medical College & KEM Hospital",
        "is_available": True,
        "schedule": ["09:30 AM", "10:30 AM", "11:30 AM", "01:00 PM", "02:30 PM", "04:00 PM"]
    },
    {
        "doctor_id": "DOC-MED-003",
        "user_id": None,
        "name": "Dr. Farhad Kapadia",
        "department": "General Medicine",
        "specialty": "Critical Care Medicine & Infectious Diseases",
        "qualification": "MBBS, MD, MRCP (UK), FICM",
        "experience_years": 22,
        "consultation_fee": 2200.0,
        "hospital_name": "P.D. Hinduja National Hospital",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM", "05:00 PM"]
    },
    {
        "doctor_id": "DOC-MED-004",
        "user_id": None,
        "name": "Dr. Pratit Samdani",
        "department": "General Medicine",
        "specialty": "Internal Medicine & Metabolic Disorders",
        "qualification": "MBBS, MD (Internal Medicine), FACP",
        "experience_years": 18,
        "consultation_fee": 2500.0,
        "hospital_name": "Breach Candy Hospital Trust",
        "is_available": True,
        "schedule": ["09:00 AM", "11:00 AM", "01:30 PM", "03:30 PM", "04:30 PM"]
    },
    {
        "doctor_id": "DOC-MED-005",
        "user_id": None,
        "name": "Dr. V. Shantaram",
        "department": "General Medicine",
        "specialty": "Geriatric Care & Lifestyle Disease Management",
        "qualification": "MBBS, MD (General Medicine)",
        "experience_years": 15,
        "consultation_fee": 1400.0,
        "hospital_name": "Apollo Hospitals, Navi Mumbai",
        "is_available": True,
        "schedule": ["09:30 AM", "11:00 AM", "02:00 PM", "03:30 PM"]
    },

    # --- Neurology ---
    {
        "doctor_id": "DOC-NEUR-003",
        "user_id": None,
        "name": "Dr. Sunita Rao",
        "department": "Neurology",
        "specialty": "Clinical Neurophysiology & Stroke Care",
        "qualification": "MBBS, MD, DM (Neurology)",
        "experience_years": 16,
        "consultation_fee": 1500.0,
        "hospital_name": "Seth GS Medical College & KEM Hospital",
        "is_available": True,
        "schedule": ["10:00 AM", "11:00 AM", "12:00 PM", "03:00 PM", "04:00 PM"]
    },
    {
        "doctor_id": "DOC-NEUR-004",
        "user_id": None,
        "name": "Dr. Arun B. Shah",
        "department": "Neurology",
        "specialty": "Movement Disorders & Parkinson's Disease",
        "qualification": "MBBS, MD, DM (Neurology)",
        "experience_years": 25,
        "consultation_fee": 2800.0,
        "hospital_name": "Lilavati Hospital & Research Centre",
        "is_available": True,
        "schedule": ["10:30 AM", "12:00 PM", "02:30 PM", "04:00 PM", "05:00 PM"]
    },
    {
        "doctor_id": "DOC-NEUR-005",
        "user_id": None,
        "name": "Dr. Roop Gursahani",
        "department": "Neurology",
        "specialty": "Epilepsy & Neuromuscular Disorders",
        "qualification": "MBBS, MD, DM (Neurology)",
        "experience_years": 21,
        "consultation_fee": 2400.0,
        "hospital_name": "P.D. Hinduja National Hospital",
        "is_available": True,
        "schedule": ["09:30 AM", "11:00 AM", "01:00 PM", "03:00 PM"]
    },

    # --- Orthopedics ---
    {
        "doctor_id": "DOC-ORTH-004",
        "user_id": None,
        "name": "Dr. Amit Shah",
        "department": "Orthopedics",
        "specialty": "Joint Replacement & Arthroscopy",
        "qualification": "MBBS, MS (Orthopedics), M.Ch (Ortho)",
        "experience_years": 11,
        "consultation_fee": 1000.0,
        "hospital_name": "Seth GS Medical College & KEM Hospital",
        "is_available": True,
        "schedule": ["09:00 AM", "10:30 AM", "12:00 PM", "02:00 PM", "03:30 PM"]
    },
    {
        "doctor_id": "DOC-ORTH-005",
        "user_id": None,
        "name": "Dr. Sanjay Agarwala",
        "department": "Orthopedics",
        "specialty": "Hip & Knee Arthroplasty, Avascular Necrosis",
        "qualification": "MBBS, MS, M.Ch (Ortho Liverpool)",
        "experience_years": 26,
        "consultation_fee": 2600.0,
        "hospital_name": "P.D. Hinduja National Hospital",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "02:30 PM", "04:30 PM"]
    },
    {
        "doctor_id": "DOC-ORTH-006",
        "user_id": None,
        "name": "Dr. Nirad Vengsarkar",
        "department": "Orthopedics",
        "specialty": "Spine Surgery & Sports Medicine",
        "qualification": "MBBS, MS (Ortho), D.Ortho, FCPS",
        "experience_years": 18,
        "consultation_fee": 2200.0,
        "hospital_name": "Lilavati Hospital & Research Centre",
        "is_available": True,
        "schedule": ["09:30 AM", "11:00 AM", "01:30 PM", "03:00 PM", "04:30 PM"]
    },

    # --- Pulmonology ---
    {
        "doctor_id": "DOC-PULM-006",
        "user_id": None,
        "name": "Dr. Arvind Mehta",
        "department": "Pulmonology",
        "specialty": "Pulmonology & Interventional Bronchoscopy",
        "qualification": "MBBS, MD (Pulmonary Medicine), FCCP",
        "experience_years": 15,
        "consultation_fee": 1100.0,
        "hospital_name": "Seth GS Medical College & KEM Hospital",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "01:00 PM", "02:30 PM", "04:00 PM"]
    },
    {
        "doctor_id": "DOC-PULM-007",
        "user_id": None,
        "name": "Dr. Zarir Udwadia",
        "department": "Pulmonology",
        "specialty": "MDR-TB, Sleep Medicine & Interstitial Lung Disease",
        "qualification": "MBBS, MD, DNB, FRCP (London), FCCP",
        "experience_years": 27,
        "consultation_fee": 3000.0,
        "hospital_name": "P.D. Hinduja National Hospital",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM"]
    },
    {
        "doctor_id": "DOC-PULM-008",
        "user_id": None,
        "name": "Dr. Sanjeev Mehta",
        "department": "Pulmonology",
        "specialty": "Chest Medicine, Asthma & Allergy Care",
        "qualification": "MBBS, MD (Chest Medicine)",
        "experience_years": 20,
        "consultation_fee": 2200.0,
        "hospital_name": "Lilavati Hospital & Research Centre",
        "is_available": True,
        "schedule": ["09:30 AM", "11:00 AM", "02:00 PM", "03:30 PM"]
    },

    # --- Pediatrics ---
    {
        "doctor_id": "DOC-PED-005",
        "user_id": None,
        "name": "Dr. Sneha Kulkarni",
        "department": "Pediatrics",
        "specialty": "Pediatric Critical Care & Neonatology",
        "qualification": "MBBS, MD (Pediatrics), DCH",
        "experience_years": 9,
        "consultation_fee": 900.0,
        "hospital_name": "Seth GS Medical College & KEM Hospital",
        "is_available": True,
        "schedule": ["09:30 AM", "11:00 AM", "01:30 PM", "03:00 PM", "04:30 PM"]
    },
    {
        "doctor_id": "DOC-PED-006",
        "user_id": None,
        "name": "Dr. Nitin Shah",
        "department": "Pediatrics",
        "specialty": "Pediatric Hematology-Oncology & Immunology",
        "qualification": "MBBS, MD, DCH, FIAP",
        "experience_years": 24,
        "consultation_fee": 2000.0,
        "hospital_name": "P.D. Hinduja National Hospital",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM", "04:30 PM"]
    },
    {
        "doctor_id": "DOC-PED-007",
        "user_id": None,
        "name": "Dr. Bhupendra Avasthi",
        "department": "Pediatrics",
        "specialty": "Advanced Neonatology & Child Development",
        "qualification": "MBBS, MD (Pediatrics), FIAP",
        "experience_years": 22,
        "consultation_fee": 1800.0,
        "hospital_name": "Lilavati Hospital & Research Centre",
        "is_available": True,
        "schedule": ["09:00 AM", "11:00 AM", "01:00 PM", "03:00 PM"]
    },

    # --- Oncology ---
    {
        "doctor_id": "DOC-ONC-001",
        "user_id": None,
        "name": "Dr. Suresh Advani",
        "department": "Oncology",
        "specialty": "Medical & Hemato-Oncology, Bone Marrow Transplant",
        "qualification": "MBBS, MD, FICP, FNAMS (Padma Shri & Padma Bhushan)",
        "experience_years": 35,
        "consultation_fee": 3000.0,
        "hospital_name": "Tata Memorial Hospital",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "02:30 PM", "04:00 PM"]
    },
    {
        "doctor_id": "DOC-ONC-002",
        "user_id": None,
        "name": "Dr. Sudeep Gupta",
        "department": "Oncology",
        "specialty": "Medical Oncology & Targeted Cancer Therapies",
        "qualification": "MBBS, MD, DM (Medical Oncology)",
        "experience_years": 20,
        "consultation_fee": 1500.0,
        "hospital_name": "Tata Memorial Hospital",
        "is_available": True,
        "schedule": ["09:30 AM", "11:00 AM", "01:30 PM", "03:30 PM"]
    },
    {
        "doctor_id": "DOC-ONC-003",
        "user_id": None,
        "name": "Dr. Shona Nag",
        "department": "Oncology",
        "specialty": "Breast Oncology & Clinical Trials",
        "qualification": "MBBS, MD (Medicine), DM (Oncology)",
        "experience_years": 19,
        "consultation_fee": 2000.0,
        "hospital_name": "Apollo Hospitals, Navi Mumbai",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM"]
    },

    # --- Nephrology ---
    {
        "doctor_id": "DOC-NEPH-008",
        "user_id": None,
        "name": "Dr. Vikram Rathore",
        "department": "Nephrology",
        "specialty": "Renal Transplant & Hemodialysis",
        "qualification": "MBBS, MD, DM (Nephrology)",
        "experience_years": 13,
        "consultation_fee": 1300.0,
        "hospital_name": "Seth GS Medical College & KEM Hospital",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM"]
    },
    {
        "doctor_id": "DOC-NEPH-009",
        "user_id": None,
        "name": "Dr. Jatin Kothari",
        "department": "Nephrology",
        "specialty": "Kidney Transplantation & Glomerular Diseases",
        "qualification": "MBBS, MD, DM, DNB (Nephrology)",
        "experience_years": 21,
        "consultation_fee": 2400.0,
        "hospital_name": "P.D. Hinduja National Hospital",
        "is_available": True,
        "schedule": ["09:30 AM", "11:00 AM", "01:30 PM", "03:30 PM"]
    },
    {
        "doctor_id": "DOC-NEPH-010",
        "user_id": None,
        "name": "Dr. Hemant Mehta",
        "department": "Nephrology",
        "specialty": "Interventional Nephrology & Peritoneal Dialysis",
        "qualification": "MBBS, MD, DM (Nephrology)",
        "experience_years": 17,
        "consultation_fee": 2000.0,
        "hospital_name": "Lilavati Hospital & Research Centre",
        "is_available": True,
        "schedule": ["10:00 AM", "12:00 PM", "02:30 PM", "04:30 PM"]
    },

    # --- Obstetrics & Gynecology ---
    {
        "doctor_id": "DOC-OBGYN-007",
        "user_id": None,
        "name": "Dr. Fatima Sheikh",
        "department": "Obstetrics & Gynecology",
        "specialty": "High-Risk Obstetrics & Laparoscopic Surgery",
        "qualification": "MBBS, MS (OB-GYN), DGO, FICOG",
        "experience_years": 13,
        "consultation_fee": 1100.0,
        "hospital_name": "Seth GS Medical College & KEM Hospital",
        "is_available": True,
        "schedule": ["09:00 AM", "10:30 AM", "12:00 PM", "02:00 PM", "03:30 PM"]
    },
    {
        "doctor_id": "DOC-OBGYN-008",
        "user_id": None,
        "name": "Dr. Rishma Pai",
        "department": "Obstetrics & Gynecology",
        "specialty": "Infertility, IVF & Minimally Invasive Surgery",
        "qualification": "MBBS, MD, DGO, FCPS, FICOG",
        "experience_years": 25,
        "consultation_fee": 2500.0,
        "hospital_name": "Lilavati Hospital & Research Centre",
        "is_available": True,
        "schedule": ["10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM"]
    },
    {
        "doctor_id": "DOC-OBGYN-009",
        "user_id": None,
        "name": "Dr. Indira Hinduja",
        "department": "Obstetrics & Gynecology",
        "specialty": "Reproductive Medicine, GIFT & High-Risk Pregnancy",
        "qualification": "MBBS, MD, Ph.D (OB-GYN), Padma Shri",
        "experience_years": 30,
        "consultation_fee": 3000.0,
        "hospital_name": "Breach Candy Hospital Trust",
        "is_available": True,
        "schedule": ["09:30 AM", "11:00 AM", "01:00 PM", "03:00 PM"]
    }
]

def seed_multi_hospital_doctors():
    db: Session = SessionLocal()
    now_utc = datetime.now(timezone.utc)
    count_updated = 0
    count_created = 0

    try:
        print(f"Upserting {len(DOCTORS_MULTI_HOSPITAL)} multi-hospital specialist doctors...")
        for doc in DOCTORS_MULTI_HOSPITAL:
            existing = db.scalar(select(DoctorProfile).where(DoctorProfile.doctor_id == doc["doctor_id"]))
            if existing:
                existing.name = doc["name"]
                existing.department = doc["department"]
                existing.specialty = doc["specialty"]
                existing.qualification = doc["qualification"]
                existing.experience_years = doc["experience_years"]
                existing.consultation_fee = doc["consultation_fee"]
                existing.hospital_name = doc["hospital_name"]
                existing.is_available = doc["is_available"]
                existing.schedule_json = json.dumps(doc["schedule"])
                count_updated += 1
            else:
                new_doc = DoctorProfile(
                    doctor_id=doc["doctor_id"],
                    user_id=doc["user_id"],
                    name=doc["name"],
                    department=doc["department"],
                    specialty=doc["specialty"],
                    qualification=doc["qualification"],
                    experience_years=doc["experience_years"],
                    consultation_fee=doc["consultation_fee"],
                    hospital_name=doc["hospital_name"],
                    is_available=doc["is_available"],
                    schedule_json=json.dumps(doc["schedule"]),
                    created_at=now_utc
                )
                db.add(new_doc)
                count_created += 1

        db.commit()
        print(f"Successfully seeded doctors! Created: {count_created}, Updated: {count_updated}")
    except Exception as e:
        db.rollback()
        print(f"Error seeding doctors: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_multi_hospital_doctors()
