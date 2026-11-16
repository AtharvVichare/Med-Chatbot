"""
Billing & Revenue Cycle Management Router
Provides:
- Invoices listing & financial summaries
- Automated invoice creation with assisted ICD-10 coding
- Payment tracking & collection records
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.db.models import BillingInvoice, Patient
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User
from backend.app.services.agents.billing_rcm_agent import BillingRCMAgent

router = APIRouter(prefix="/billing", tags=["Billing & RCM"])

class GenerateInvoiceRequest(BaseModel):
    patient_id: str
    items: List[Dict[str, Any]]
    insurance_percentage: float = 70.0
    clinical_context: Optional[str] = None

class PayInvoiceRequest(BaseModel):
    payment_method: str = "online_upi"

@router.get("/invoices")
def list_invoices(
    patient_id: Optional[str] = None,
    payment_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists invoices with role-based visibility."""
    stmt = select(BillingInvoice)
    if current_user.role == "patient" and current_user.patient_id:
        stmt = stmt.where(BillingInvoice.patient_id == current_user.patient_id)
    elif patient_id:
        stmt = stmt.where(BillingInvoice.patient_id == patient_id)

    if payment_status:
        stmt = stmt.where(BillingInvoice.payment_status == payment_status)

    stmt = stmt.order_by(BillingInvoice.invoice_date.desc(), BillingInvoice.created_at.desc())
    invoices = db.scalars(stmt).all()

    import json
    results = []
    for inv in invoices:
        pat = db.scalar(select(Patient).where(Patient.patient_id == inv.patient_id))
        try:
            items = json.loads(inv.items_json)
        except Exception:
            items = []
        try:
            icd = json.loads(inv.icd10_codes_json)
        except Exception:
            icd = []

        results.append({
            "invoice_id": inv.invoice_id,
            "patient_id": inv.patient_id,
            "patient_name": f"{pat.first_name} {pat.last_name}" if pat else inv.patient_id,
            "invoice_date": str(inv.invoice_date),
            "total_amount": inv.total_amount,
            "insurance_covered": inv.insurance_covered,
            "patient_payable": inv.patient_payable,
            "payment_status": inv.payment_status,
            "items": items,
            "icd10_codes": icd,
            "coded_by": inv.coded_by,
            "approved_by": inv.approved_by,
            "created_at": inv.created_at.isoformat() if inv.created_at else None
        })
    return results

@router.get("/summary")
def get_revenue_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Provides revenue cycle metrics for hospital management."""
    return BillingRCMAgent.get_revenue_cycle_summary(db)

@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_invoice(
    req: GenerateInvoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates an itemized invoice with automated ICD-10 assistance."""
    try:
        return BillingRCMAgent.generate_patient_invoice(
            patient_id=req.patient_id,
            items=req.items,
            insurance_percentage=req.insurance_percentage,
            clinical_context=req.clinical_context,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{invoice_id}/pay")
def pay_invoice(
    invoice_id: str,
    req: PayInvoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Records payment for a patient invoice."""
    inv = db.scalar(select(BillingInvoice).where(BillingInvoice.invoice_id == invoice_id))
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    inv.payment_status = "paid"
    db.commit()
    return {
        "invoice_id": inv.invoice_id,
        "payment_status": "paid",
        "message": f"Payment of ₹{inv.patient_payable:,.2f} recorded successfully via {req.payment_method}."
    }
