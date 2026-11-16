"""
Procurement & Pharmacy Inventory Router
Provides:
- Inventory listing with stock and expiry filters
- AI inventory audit with critical shortages & low stock alerts
- Purchase order tracking & automated draft creation
- Human authorization workflows for hospital management
"""

from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.db.models import ProcurementInventory, ProcurementPurchaseOrder
from backend.app.core.dependencies import get_current_user
from backend.app.core.demo_users import User
from backend.app.services.agents.procurement_agent import ProcurementAgent

router = APIRouter(prefix="/inventory", tags=["Procurement & Pharmacy"])

class AuthorizePORequest(BaseModel):
    action: str  # "approve" or "reject"
    notes: Optional[str] = None

class CreatePODraftRequest(BaseModel):
    item_id: str
    quantity: int
    notes: Optional[str] = None

@router.get("/items")
def list_inventory_items(
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists medicines, equipment, and consumables."""
    stmt = select(ProcurementInventory)
    if category:
        stmt = stmt.where(ProcurementInventory.category == category)
    if status_filter:
        stmt = stmt.where(ProcurementInventory.status == status_filter)

    items = db.scalars(stmt.order_by(ProcurementInventory.name.asc())).all()
    return [
        {
            "item_id": i.item_id,
            "name": i.name,
            "category": i.category,
            "current_stock": i.current_stock,
            "unit": i.unit,
            "reorder_threshold": i.reorder_threshold,
            "reorder_quantity": i.reorder_quantity,
            "unit_price": i.unit_price,
            "supplier_name": i.supplier_name,
            "supplier_contact": i.supplier_contact,
            "expiry_date": str(i.expiry_date) if i.expiry_date else None,
            "batch_number": i.batch_number,
            "status": i.status
        }
        for i in items
    ]

@router.get("/audit")
def audit_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Runs automated Procurement Agent audit on stock levels and expiries."""
    return ProcurementAgent.audit_inventory(db)

@router.get("/purchase-orders")
def list_purchase_orders(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists purchase orders with approval status."""
    stmt = select(ProcurementPurchaseOrder)
    if status_filter:
        stmt = stmt.where(ProcurementPurchaseOrder.status == status_filter)

    orders = db.scalars(stmt.order_by(ProcurementPurchaseOrder.created_at.desc())).all()
    results = []
    for o in orders:
        item = db.scalar(select(ProcurementInventory).where(ProcurementInventory.item_id == o.item_id))
        results.append({
            "po_id": o.po_id,
            "item_id": o.item_id,
            "item_name": item.name if item else o.item_id,
            "unit": item.unit if item else "units",
            "quantity": o.quantity,
            "estimated_cost": o.estimated_cost,
            "supplier_name": o.supplier_name,
            "generated_by": o.generated_by,
            "status": o.status,
            "approval_notes": o.approval_notes,
            "approved_by": o.approved_by,
            "created_at": o.created_at.isoformat() if o.created_at else None
        })
    return results

@router.post("/purchase-orders/{po_id}/authorize")
def authorize_purchase_order(
    po_id: str,
    req: AuthorizePORequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Authorizes or rejects an AI-drafted purchase order."""
    if req.action not in ["approve", "reject"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be 'approve' or 'reject'")

    try:
        return ProcurementAgent.authorize_purchase_order(
            po_id=po_id,
            action=req.action,
            approved_by=current_user.full_name or current_user.username,
            notes=req.notes,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
