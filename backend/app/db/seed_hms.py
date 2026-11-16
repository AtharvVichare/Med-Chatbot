"""
HMS 100-Bed Facility, Doctor Directory, and Procurement Seeder for Aarogya-Drishti.
Populates:
1. 100 hospital beds across 10 wards with realistic occupancy.
2. Verified multi-specialty doctor profiles with schedule slots.
3. Procurement inventory (medicines, IV solutions, consumables, equipment).
4. Initial pending EHR updates for Doctor verification workflow.
5. Realistic billing records and initial appointment bookings.
"""

import uuid
import json
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    BedRegistry,
    DoctorProfile,
    ProcurementInventory,
    ProcurementPurchaseOrder,
    PendingEHRUpdate,
    AppointmentBooking,
    AdmissionRequest,
    BillingInvoice,
    Patient,
    Encounter
)

def seed_hms_data():
    db: Session = SessionLocal()
    try:
        print("Checking if HMS data is already seeded...")
        existing_beds = db.scalar(select(BedRegistry))
        if existing_beds:
            print("HMS beds already exist in database. Skipping bed generation.")
        else:
            print("Seeding 100-bed facility...")
            # Fetch sample patients to assign occupancy
            sample_patients = db.scalars(select(Patient).limit(70)).all()
            pat_idx = 0

            # 10 Wards totaling 100 beds
            wards_config = [
                {"ward": "ICU", "prefix": "ICU", "type": "ICU", "count": 10, "charge": 6500.0, "occ_target": 7},
                {"ward": "CCU", "prefix": "CCU", "type": "Telemetry", "count": 8, "charge": 5800.0, "occ_target": 6},
                {"ward": "Emergency", "prefix": "EMR", "type": "Standard", "count": 12, "charge": 3000.0, "occ_target": 9},
                {"ward": "General Male", "prefix": "GEN-M", "type": "Standard", "count": 15, "charge": 1200.0, "occ_target": 11},
                {"ward": "General Female", "prefix": "GEN-F", "type": "Standard", "count": 15, "charge": 1200.0, "occ_target": 10},
                {"ward": "Pediatric", "prefix": "PED", "type": "Pediatric", "count": 10, "charge": 1800.0, "occ_target": 6},
                {"ward": "Maternity", "prefix": "MAT", "type": "Standard", "count": 10, "charge": 2500.0, "occ_target": 7},
                {"ward": "Deluxe Private", "prefix": "DLX", "type": "Private Room", "count": 8, "charge": 5000.0, "occ_target": 5},
                {"ward": "Isolation", "prefix": "ISO", "type": "Negative Pressure Isolation", "count": 6, "charge": 4500.0, "occ_target": 3},
                {"ward": "Post-Op Surgical", "prefix": "SURG", "type": "Surgical Recovery", "count": 6, "charge": 3800.0, "occ_target": 4},
            ]

            now_utc = datetime.now(timezone.utc)
            for w in wards_config:
                occ_count = 0
                for i in range(1, w["count"] + 1):
                    bed_num = f"{w['prefix']}-{i:02d}"
                    should_occupy = occ_count < w["occ_target"] and pat_idx < len(sample_patients)
                    cur_pat = sample_patients[pat_idx] if should_occupy else None
                    if should_occupy:
                        occ_count += 1
                        pat_idx += 1

                    bed = BedRegistry(
                        bed_id=f"BED-{w['prefix']}-{i:02d}",
                        bed_number=bed_num,
                        ward=w["ward"],
                        bed_type=w["type"],
                        is_occupied=should_occupy,
                        current_patient_id=cur_pat.patient_id if cur_pat else None,
                        daily_charge=w["charge"],
                        status="occupied" if should_occupy else ("cleaning" if i % 7 == 0 else "available"),
                        notes=f"{w['ward']} bed equipped with multi-para monitor" if "ICU" in w["ward"] or "CCU" in w["ward"] else f"Standard care bed in {w['ward']}",
                        created_at=now_utc,
                        updated_at=now_utc
                    )
                    db.add(bed)

            db.commit()
            print(f"Successfully seeded 100 beds with {pat_idx} occupied beds!")

        # 2. Seed Doctor Profiles
        existing_doc = db.scalar(select(DoctorProfile))
        if not existing_doc:
            print("Seeding verified multi-specialty Doctor Profiles...")
            doctors_data = [
                {
                    "doctor_id": "DOC-CARD-001",
                    "user_id": "doctor_user",
                    "name": "Dr. Priya Deshmukh",
                    "department": "Cardiology",
                    "specialty": "Interventional Cardiology",
                    "qualification": "MBBS, MD (Medicine), DM (Cardiology), FACC",
                    "experience_years": 14,
                    "consultation_fee": 1200.0,
                    "is_available": True,
                    "schedule": ["09:00 AM", "10:00 AM", "11:30 AM", "02:00 PM", "03:30 PM", "04:30 PM"]
                },
                {
                    "doctor_id": "DOC-MED-002",
                    "user_id": None,
                    "name": "Dr. Rajesh Kumar",
                    "department": "General Medicine",
                    "specialty": "Internal Medicine & Diabetology",
                    "qualification": "MBBS, MD (Internal Medicine), PGD (Diabetology)",
                    "experience_years": 12,
                    "consultation_fee": 800.0,
                    "is_available": True,
                    "schedule": ["09:30 AM", "10:30 AM", "11:30 AM", "01:00 PM", "02:30 PM", "04:00 PM"]
                },
                {
                    "doctor_id": "DOC-NEUR-003",
                    "user_id": None,
                    "name": "Dr. Sunita Rao",
                    "department": "Neurology",
                    "specialty": "Clinical Neurophysiology & Stroke Care",
                    "qualification": "MBBS, MD, DM (Neurology)",
                    "experience_years": 16,
                    "consultation_fee": 1500.0,
                    "is_available": True,
                    "schedule": ["10:00 AM", "11:00 AM", "12:00 PM", "03:00 PM", "04:00 PM"]
                },
                {
                    "doctor_id": "DOC-ORTH-004",
                    "user_id": None,
                    "name": "Dr. Amit Shah",
                    "department": "Orthopedics",
                    "specialty": "Joint Replacement & Arthroscopy",
                    "qualification": "MBBS, MS (Orthopedics), M.Ch (Ortho)",
                    "experience_years": 11,
                    "consultation_fee": 1000.0,
                    "is_available": True,
                    "schedule": ["09:00 AM", "10:30 AM", "12:00 PM", "02:00 PM", "03:30 PM"]
                },
                {
                    "doctor_id": "DOC-PED-005",
                    "user_id": None,
                    "name": "Dr. Sneha Kulkarni",
                    "department": "Pediatrics",
                    "specialty": "Pediatric Critical Care & Neonatology",
                    "qualification": "MBBS, MD (Pediatrics), DCH",
                    "experience_years": 9,
                    "consultation_fee": 900.0,
                    "is_available": True,
                    "schedule": ["09:30 AM", "11:00 AM", "01:30 PM", "03:00 PM", "04:30 PM"]
                },
                {
                    "doctor_id": "DOC-PULM-006",
                    "user_id": None,
                    "name": "Dr. Arvind Mehta",
                    "department": "Pulmonology",
                    "specialty": "Interventional Pulmonology & Sleep Medicine",
                    "qualification": "MBBS, MD (Pulmonary Medicine), DNB",
                    "experience_years": 15,
                    "consultation_fee": 1100.0,
                    "is_available": True,
                    "schedule": ["10:00 AM", "11:30 AM", "02:30 PM", "04:00 PM", "05:00 PM"]
                },
                {
                    "doctor_id": "DOC-OBGYN-007",
                    "user_id": None,
                    "name": "Dr. Fatima Sheikh",
                    "department": "Obstetrics & Gynecology",
                    "specialty": "High-Risk Obstetrics & Laparoscopic Surgery",
                    "qualification": "MBBS, MS (OB-GYN), DGO",
                    "experience_years": 13,
                    "consultation_fee": 1000.0,
                    "is_available": True,
                    "schedule": ["09:00 AM", "10:30 AM", "12:30 PM", "02:00 PM", "03:30 PM"]
                },
                {
                    "doctor_id": "DOC-NEPH-008",
                    "user_id": None,
                    "name": "Dr. Vikram Rathore",
                    "department": "Nephrology",
                    "specialty": "Renal Transplant & Hemodialysis",
                    "qualification": "MBBS, MD, DM (Nephrology)",
                    "experience_years": 10,
                    "consultation_fee": 1300.0,
                    "is_available": True,
                    "schedule": ["10:30 AM", "11:30 AM", "02:00 PM", "03:30 PM", "04:30 PM"]
                }
            ]

            for d in doctors_data:
                doc_obj = DoctorProfile(
                    doctor_id=d["doctor_id"],
                    user_id=d["user_id"],
                    name=d["name"],
                    department=d["department"],
                    specialty=d["specialty"],
                    qualification=d["qualification"],
                    experience_years=d["experience_years"],
                    consultation_fee=d["consultation_fee"],
                    is_available=d["is_available"],
                    schedule_json=json.dumps(d["schedule"]),
                    created_at=datetime.now(timezone.utc)
                )
                db.add(doc_obj)
            db.commit()
            print("Successfully seeded 8 verified multi-specialty Doctor Profiles!")

        # 3. Seed Procurement Inventory
        existing_inv = db.scalar(select(ProcurementInventory))
        if not existing_inv:
            print("Seeding Procurement Inventory...")
            inventory_items = [
                # Critical / Low Stock items
                {
                    "item_id": "INV-MED-001",
                    "name": "Insulin Glargine 100 IU/ml (Lantus)",
                    "category": "medicine",
                    "current_stock": 14,
                    "unit": "vials",
                    "reorder_threshold": 30,
                    "reorder_quantity": 100,
                    "unit_price": 580.0,
                    "supplier_name": "Sanofi Healthcare India",
                    "supplier_contact": "supply@sanofi.in",
                    "expiry_date": date.today() + timedelta(days=240),
                    "batch_number": "SNF-2026-B81",
                    "status": "low_stock"
                },
                {
                    "item_id": "INV-MED-002",
                    "name": "Atorvastatin 20mg Tablets",
                    "category": "medicine",
                    "current_stock": 450,
                    "unit": "strips",
                    "reorder_threshold": 100,
                    "reorder_quantity": 500,
                    "unit_price": 65.0,
                    "supplier_name": "Sun Pharma Industries",
                    "supplier_contact": "orders@sunpharma.com",
                    "expiry_date": date.today() + timedelta(days=500),
                    "batch_number": "SUN-7729-A",
                    "status": "in_stock"
                },
                {
                    "item_id": "INV-MED-003",
                    "name": "Metformin 500mg SR Tablets",
                    "category": "medicine",
                    "current_stock": 620,
                    "unit": "strips",
                    "reorder_threshold": 150,
                    "reorder_quantity": 600,
                    "unit_price": 32.0,
                    "supplier_name": "USV Pvt Ltd",
                    "supplier_contact": "distribution@usv.in",
                    "expiry_date": date.today() + timedelta(days=420),
                    "batch_number": "USV-5510-C",
                    "status": "in_stock"
                },
                {
                    "item_id": "INV-MED-004",
                    "name": "Amlodipine 5mg Tablets",
                    "category": "medicine",
                    "current_stock": 25,
                    "unit": "strips",
                    "reorder_threshold": 80,
                    "reorder_quantity": 400,
                    "unit_price": 28.0,
                    "supplier_name": "Cipla Pharmaceuticals",
                    "supplier_contact": "hospitalcare@cipla.com",
                    "expiry_date": date.today() + timedelta(days=360),
                    "batch_number": "CIP-3391",
                    "status": "critical"
                },
                {
                    "item_id": "INV-MED-005",
                    "name": "Enoxaparin Sodium 40mg/0.4ml Pre-filled Syringes (Clexane)",
                    "category": "medicine",
                    "current_stock": 8,
                    "unit": "syringes",
                    "reorder_threshold": 25,
                    "reorder_quantity": 80,
                    "unit_price": 420.0,
                    "supplier_name": "Sanofi Healthcare India",
                    "supplier_contact": "supply@sanofi.in",
                    "expiry_date": date.today() + timedelta(days=180),
                    "batch_number": "SNF-4412",
                    "status": "critical"
                },
                {
                    "item_id": "INV-MED-006",
                    "name": "Piperacillin + Tazobactam 4.5g Injection",
                    "category": "medicine",
                    "current_stock": 18,
                    "unit": "vials",
                    "reorder_threshold": 40,
                    "reorder_quantity": 150,
                    "unit_price": 340.0,
                    "supplier_name": "Alkem Laboratories",
                    "supplier_contact": "institutional@alkem.com",
                    "expiry_date": date.today() + timedelta(days=290),
                    "batch_number": "ALK-9982",
                    "status": "low_stock"
                },
                {
                    "item_id": "INV-MED-007",
                    "name": "Normal Saline 0.9% IV 500ml",
                    "category": "consumable",
                    "current_stock": 380,
                    "unit": "bottles",
                    "reorder_threshold": 120,
                    "reorder_quantity": 500,
                    "unit_price": 38.0,
                    "supplier_name": "Fresenius Kabi India",
                    "supplier_contact": "sales@fresenius.in",
                    "expiry_date": date.today() + timedelta(days=600),
                    "batch_number": "FK-00129",
                    "status": "in_stock"
                },
                {
                    "item_id": "INV-MED-008",
                    "name": "Ringer Lactate (RL) IV 500ml",
                    "category": "consumable",
                    "current_stock": 42,
                    "unit": "bottles",
                    "reorder_threshold": 100,
                    "reorder_quantity": 400,
                    "unit_price": 42.0,
                    "supplier_name": "Fresenius Kabi India",
                    "supplier_contact": "sales@fresenius.in",
                    "expiry_date": date.today() + timedelta(days=550),
                    "batch_number": "FK-00284",
                    "status": "low_stock"
                },
                {
                    "item_id": "INV-MED-009",
                    "name": "N95 Particulate Respirator Masks (Box of 50)",
                    "category": "consumable",
                    "current_stock": 16,
                    "unit": "boxes",
                    "reorder_threshold": 20,
                    "reorder_quantity": 60,
                    "unit_price": 950.0,
                    "supplier_name": "3M Healthcare",
                    "supplier_contact": "medorders@3m.com",
                    "expiry_date": date.today() + timedelta(days=800),
                    "batch_number": "3M-N95-2026",
                    "status": "low_stock"
                },
                {
                    "item_id": "INV-MED-010",
                    "name": "Sterile Surgical Gloves Size 7.5 (Box of 100 pairs)",
                    "category": "surgical",
                    "current_stock": 85,
                    "unit": "boxes",
                    "reorder_threshold": 30,
                    "reorder_quantity": 100,
                    "unit_price": 1200.0,
                    "supplier_name": "Ansell Healthcare",
                    "supplier_contact": "info@ansell.in",
                    "expiry_date": date.today() + timedelta(days=650),
                    "batch_number": "ANS-GLV-81",
                    "status": "in_stock"
                },
                {
                    "item_id": "INV-MED-011",
                    "name": "Multi-Parameter Bedside Monitor (5-Lead ECG, SpO2, NIBP)",
                    "category": "equipment",
                    "current_stock": 2,
                    "unit": "units",
                    "reorder_threshold": 3,
                    "reorder_quantity": 5,
                    "unit_price": 85000.0,
                    "supplier_name": "Mindray Medical India",
                    "supplier_contact": "service@mindray.in",
                    "expiry_date": None,
                    "batch_number": "MND-MPM-991",
                    "status": "low_stock"
                },
                {
                    "item_id": "INV-MED-012",
                    "name": "Syringe Infusion Pump (Dual Channel)",
                    "category": "equipment",
                    "current_stock": 5,
                    "unit": "units",
                    "reorder_threshold": 4,
                    "reorder_quantity": 6,
                    "unit_price": 42000.0,
                    "supplier_name": "B. Braun Medical India",
                    "supplier_contact": "hospital@bbraun.in",
                    "expiry_date": None,
                    "batch_number": "BBR-PUMP-2025",
                    "status": "in_stock"
                }
            ]

            now_utc = datetime.now(timezone.utc)
            for itm in inventory_items:
                inv_obj = ProcurementInventory(
                    item_id=itm["item_id"],
                    name=itm["name"],
                    category=itm["category"],
                    current_stock=itm["current_stock"],
                    unit=itm["unit"],
                    reorder_threshold=itm["reorder_threshold"],
                    reorder_quantity=itm["reorder_quantity"],
                    unit_price=itm["unit_price"],
                    supplier_name=itm["supplier_name"],
                    supplier_contact=itm["supplier_contact"],
                    expiry_date=itm["expiry_date"],
                    batch_number=itm["batch_number"],
                    status=itm["status"],
                    last_restocked_date=date.today() - timedelta(days=20),
                    created_at=now_utc,
                    updated_at=now_utc
                )
                db.add(inv_obj)

            # Add automated draft purchase orders generated by Procurement Agent
            po1 = ProcurementPurchaseOrder(
                po_id="PO-2026-001",
                item_id="INV-MED-004",
                quantity=400,
                estimated_cost=400 * 28.0,
                supplier_name="Cipla Pharmaceuticals",
                generated_by="procurement_agent",
                status="draft_pending_authorization",
                approval_notes="Auto-generated due to critical stock level (25 strips remaining; threshold 80).",
                created_at=now_utc
            )
            po2 = ProcurementPurchaseOrder(
                po_id="PO-2026-002",
                item_id="INV-MED-005",
                quantity=80,
                estimated_cost=80 * 420.0,
                supplier_name="Sanofi Healthcare India",
                generated_by="procurement_agent",
                status="draft_pending_authorization",
                approval_notes="Urgent: ICU/CCU DVT prophylaxis stock critical (8 pre-filled syringes remaining).",
                created_at=now_utc
            )
            po3 = ProcurementPurchaseOrder(
                po_id="PO-2026-003",
                item_id="INV-MED-001",
                quantity=100,
                estimated_cost=100 * 580.0,
                supplier_name="Sanofi Healthcare India",
                generated_by="procurement_agent",
                status="draft_pending_authorization",
                approval_notes="Stock level below 50% threshold. Recommended batch restock.",
                created_at=now_utc
            )
            db.add_all([po1, po2, po3])
            db.commit()
            print("Successfully seeded Procurement Inventory and 3 AI Purchase Order drafts!")

        # 4. Seed Pending EHR Updates (Doctor Verification Workflow)
        existing_pending = db.scalar(select(PendingEHRUpdate))
        if not existing_pending:
            print("Seeding Pending EHR Updates for Doctor Verification Workflow...")
            pending_items = [
                {
                    "update_id": "PND-EHR-001",
                    "patient_id": "PAT-00001",
                    "update_type": "condition",
                    "source": "patient_chat",
                    "proposed_data": json.dumps({
                        "diagnosis_name": "Mild Occasional Dyspnea on Exertion",
                        "diagnosis_code": "R06.02",
                        "onset_date": str(date.today() - timedelta(days=7)),
                        "patient_note": "Patient reported feeling short of breath when climbing 2 flights of stairs for past 1 week."
                    }),
                    "status": "pending_verification",
                    "assigned_doctor_id": "DOC-CARD-001"
                },
                {
                    "update_id": "PND-EHR-002",
                    "patient_id": "PAT-00001",
                    "update_type": "medication",
                    "source": "patient_chat",
                    "proposed_data": json.dumps({
                        "medication_name": "Over-the-counter CoQ10 Capsule",
                        "dosage": "100mg once daily with breakfast",
                        "start_date": str(date.today() - timedelta(days=3)),
                        "status": "patient_taking",
                        "patient_note": "Started dietary supplement for heart health; seeking doctor approval."
                    }),
                    "status": "pending_verification",
                    "assigned_doctor_id": "DOC-CARD-001"
                },
                {
                    "update_id": "PND-EHR-003",
                    "patient_id": "PAT-00002",
                    "update_type": "observation",
                    "source": "voice_input",
                    "proposed_data": json.dumps({
                        "test_name": "Fasting Blood Glucose (Home Glucometer)",
                        "test_code": "1558-6",
                        "value_numeric": 142.0,
                        "unit": "mg/dL",
                        "date": str(date.today()),
                        "interpretation": "High"
                    }),
                    "status": "pending_verification",
                    "assigned_doctor_id": "DOC-CARD-001"
                }
            ]

            now_utc = datetime.now(timezone.utc)
            for p in pending_items:
                upd = PendingEHRUpdate(
                    update_id=p["update_id"],
                    patient_id=p["patient_id"],
                    update_type=p["update_type"],
                    source=p["source"],
                    proposed_data=p["proposed_data"],
                    status=p["status"],
                    assigned_doctor_id=p["assigned_doctor_id"],
                    created_at=now_utc
                )
                db.add(upd)
            db.commit()
            print("Successfully seeded Pending EHR Updates for Doctor verification!")

        # 5. Seed Appointments & Admission Requests
        existing_appts = db.scalar(select(AppointmentBooking))
        if not existing_appts:
            print("Seeding initial appointments & admissions...")
            tomorrow = date.today() + timedelta(days=1)
            b1 = AppointmentBooking(
                booking_id="BKG-2026-001",
                patient_id="PAT-00001",
                doctor_id="DOC-CARD-001",
                department="Cardiology",
                booking_date=tomorrow,
                time_slot="10:00 AM",
                status="confirmed",
                chief_complaint="Follow-up consultation for blood pressure management and recent exertion breathlessness.",
                booked_via="intake_agent",
                created_at=datetime.now(timezone.utc)
            )
            b2 = AppointmentBooking(
                booking_id="BKG-2026-002",
                patient_id="PAT-00002",
                doctor_id="DOC-CARD-001",
                department="Cardiology",
                booking_date=tomorrow,
                time_slot="11:30 AM",
                status="confirmed",
                chief_complaint="Routine cardiac screening and lipid review.",
                booked_via="portal",
                created_at=datetime.now(timezone.utc)
            )
            db.add_all([b1, b2])

            adm1 = AdmissionRequest(
                request_id="ADM-2026-001",
                patient_id="PAT-00001",
                doctor_id="DOC-CARD-001",
                department="Cardiology",
                recommended_ward="CCU",
                assigned_bed_id="BED-CCU-02",
                priority="urgent",
                status="assigned",
                admission_notes="Elective monitoring for unstable angina post-stress evaluation.",
                created_at=datetime.now(timezone.utc)
            )
            db.add(adm1)
            db.commit()
            print("Successfully seeded appointments and admission requests!")

        # 6. Seed Billing Invoices
        existing_inv = db.scalar(select(BillingInvoice))
        if not existing_inv:
            print("Seeding Billing / RCM Invoices...")
            inv1 = BillingInvoice(
                invoice_id="INV-2026-001",
                patient_id="PAT-00001",
                invoice_date=date.today() - timedelta(days=5),
                total_amount=9800.0,
                insurance_covered=7500.0,
                patient_payable=2300.0,
                payment_status="paid",
                items_json=json.dumps([
                    {"description": "Specialist Consultation (Dr. Priya Deshmukh)", "category": "consultation", "amount": 1200.0},
                    {"description": "12-Lead Electrocardiogram (ECG)", "category": "procedure", "amount": 850.0},
                    {"description": "Echocardiogram (2D Echo + Doppler)", "category": "procedure", "amount": 3200.0},
                    {"description": "Complete Lipid Profile & Serum Creatinine", "category": "laboratory", "amount": 1550.0},
                    {"description": "Bedside Observation (Emergency 4 hrs)", "category": "bed", "amount": 3000.0}
                ]),
                icd10_codes_json=json.dumps([
                    {"code": "I10", "description": "Essential (primary) hypertension"},
                    {"code": "I20.9", "description": "Angina pectoris, unspecified"},
                    {"code": "Z01.810", "description": "Encounter for preprocedural cardiovascular examination"}
                ]),
                coded_by="billing_rcm_agent",
                approved_by="Dr. Priya Deshmukh",
                created_at=datetime.now(timezone.utc)
            )

            inv2 = BillingInvoice(
                invoice_id="INV-2026-002",
                patient_id="PAT-00002",
                invoice_date=date.today() - timedelta(days=1),
                total_amount=5400.0,
                insurance_covered=4000.0,
                patient_payable=1400.0,
                payment_status="pending",
                items_json=json.dumps([
                    {"description": "Internal Medicine Consultation (Dr. Rajesh Kumar)", "category": "consultation", "amount": 800.0},
                    {"description": "HbA1c Glycated Hemoglobin Test", "category": "laboratory", "amount": 950.0},
                    {"description": "Kidney Function Test (KFT)", "category": "laboratory", "amount": 1250.0},
                    {"description": "Pharmacy: Metformin & Atorvastatin (30 days)", "category": "pharmacy", "amount": 900.0},
                    {"description": "Day Care Clinical Monitoring", "category": "bed", "amount": 1500.0}
                ]),
                icd10_codes_json=json.dumps([
                    {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications"},
                    {"code": "E78.5", "description": "Hyperlipidemia, unspecified"}
                ]),
                coded_by="billing_rcm_agent",
                approved_by=None,
                created_at=datetime.now(timezone.utc)
            )
            db.add_all([inv1, inv2])
            db.commit()
            print("Successfully seeded Billing Invoices!")

        print("HMS Database Seeding Complete!")

    except Exception as e:
        print(f"Error seeding HMS data: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_hms_data()
