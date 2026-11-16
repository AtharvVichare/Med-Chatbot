"""
Billing & Revenue Cycle Management (RCM) Agent for Aarogya-Drishti HMS.
Manages:
- Automated invoice drafting & line items (bed, consultations, procedures, lab)
- ICD-10 coding assistance with clinical rationale
- Revenue cycle tracking (billed, paid, insurance coverage, outstanding)
- Human authorization workflows for financial adjustments
"""

import uuid
import json
import logging
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.app.db.models import (
    BillingInvoice,
    Patient,
    BedRegistry,
    AdmissionRequest,
    Condition
)
from backend.app.services.agent_event_bus import AgentEventBus

logger = logging.getLogger("BillingRCMAgent")

# Comprehensive ICD-10 Clinical Mapping Registry
ICD10_KNOWLEDGE_BASE = {
    "hypertension": {"code": "I10", "description": "Essential (primary) hypertension", "category": "Cardiovascular"},
    "angina": {"code": "I20.9", "description": "Angina pectoris, unspecified", "category": "Cardiovascular"},
    "coronary artery disease": {"code": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery", "category": "Cardiovascular"},
    "type 2 diabetes": {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications", "category": "Endocrine"},
    "type 2 diabetes with nephropathy": {"code": "E11.21", "description": "Type 2 diabetes mellitus with diabetic nephropathy", "category": "Endocrine"},
    "hyperlipidemia": {"code": "E78.5", "description": "Hyperlipidemia, unspecified", "category": "Endocrine"},
    "asthma": {"code": "J45.909", "description": "Unspecified asthma, uncomplicated", "category": "Respiratory"},
    "copd": {"code": "J44.9", "description": "Chronic obstructive pulmonary disease, unspecified", "category": "Respiratory"},
    "acute bronchitis": {"code": "J20.9", "description": "Acute bronchitis, unspecified", "category": "Respiratory"},
    "chronic kidney disease": {"code": "N18.9", "description": "Chronic kidney disease, unspecified", "category": "Renal"},
    "migraine": {"code": "G43.909", "description": "Migraine, unspecified, not intractable", "category": "Neurological"},
    "osteoarthritis": {"code": "M19.90", "description": "Unspecified osteoarthritis, unspecified site", "category": "Musculoskeletal"}
}

class BillingRCMAgent:
    @staticmethod
    def assist_icd10_coding(clinical_text: str) -> List[Dict[str, str]]:
        """Provides automated ICD-10 coding recommendations based on clinical text or diagnoses."""
        text_low = clinical_text.lower()
        matched = []

        for condition, meta in ICD10_KNOWLEDGE_BASE.items():
            if condition in text_low or any(w in text_low for w in condition.split() if len(w) > 4):
                matched.append({
                    "code": meta["code"],
                    "description": meta["description"],
                    "category": meta["category"],
                    "clinical_rationale": f"Matched documented clinical mention: '{condition}'"
                })

        if not matched:
            matched.append({
                "code": "Z00.00",
                "description": "Encounter for general adult medical examination without abnormal findings",
                "category": "General",
                "clinical_rationale": "Default baseline encounter code"
            })

        return matched

    @staticmethod
    def generate_patient_invoice(
        patient_id: str,
        items: List[Dict[str, Any]],
        insurance_percentage: float = 70.0,
        clinical_context: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Generates an itemized patient invoice with automated ICD-10 assistance."""
        patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id))
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        total_amt = sum(item.get("amount", 0.0) for item in items)
        ins_covered = round(total_amt * (insurance_percentage / 100.0), 2)
        pat_payable = round(total_amt - ins_covered, 2)

        # Retrieve active conditions for ICD-10 assistance
        conditions = db.scalars(select(Condition).where(Condition.patient_id == patient_id)).all()
        cond_text = " ".join([c.diagnosis_name for c in conditions])
        if clinical_context:
            cond_text += " " + clinical_context

        icd_codes = BillingRCMAgent.assist_icd10_coding(cond_text)

        inv_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
        now_utc = datetime.now(timezone.utc)
        inv = BillingInvoice(
            invoice_id=inv_id,
            patient_id=patient_id,
            invoice_date=date.today(),
            total_amount=total_amt,
            insurance_covered=ins_covered,
            patient_payable=pat_payable,
            payment_status="draft",
            items_json=json.dumps(items),
            icd10_codes_json=json.dumps(icd_codes),
            coded_by="billing_rcm_agent",
            approved_by=None,
            created_at=now_utc
        )
        db.add(inv)
        db.commit()

        # Emit billing event
        AgentEventBus.emit(
            source_agent="billing_rcm_agent",
            event_type="INVOICE_GENERATED",
            payload={
                "invoice_id": inv_id,
                "patient_id": patient_id,
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "total_amount": total_amt,
                "insurance_covered": ins_covered,
                "patient_payable": pat_payable,
                "icd10_count": len(icd_codes)
            },
            target_agent="management_dashboard",
            requires_human_approval=True,
            db=db
        )

        return {
            "invoice_id": inv_id,
            "patient_id": patient_id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "invoice_date": str(date.today()),
            "total_amount": total_amt,
            "insurance_covered": ins_covered,
            "patient_payable": pat_payable,
            "payment_status": "draft",
            "items": items,
            "icd10_codes": icd_codes
        }

    @staticmethod
    def get_revenue_cycle_summary(db: Session) -> Dict[str, Any]:
        """Provides financial analytics for the Management Dashboard."""
        invoices = db.scalars(select(BillingInvoice)).all()
        total_billed = sum(i.total_amount for i in invoices)
        total_collected = sum(i.patient_payable + i.insurance_covered for i in invoices if i.payment_status == "paid")
        total_insurance = sum(i.insurance_covered for i in invoices)
        pending_collections = sum(i.patient_payable for i in invoices if i.payment_status in ["pending", "draft"])

        status_counts = {"paid": 0, "pending": 0, "draft": 0}
        for i in invoices:
            status_counts[i.payment_status] = status_counts.get(i.payment_status, 0) + 1

        return {
            "total_invoices_count": len(invoices),
            "total_billed": round(total_billed, 2),
            "total_collected": round(total_collected, 2),
            "total_insurance_claimed": round(total_insurance, 2),
            "pending_collections": round(pending_collections, 2),
            "collection_rate": round((total_collected / total_billed * 100), 1) if total_billed > 0 else 0.0,
            "status_breakdown": status_counts
        }
