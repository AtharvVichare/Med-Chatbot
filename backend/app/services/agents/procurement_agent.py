"""
Procurement Agent for Aarogya-Drishti HMS.
Monitors inventory, identifies stock shortages, flags expiries,
generates automated purchase order drafts, and routes them for human authorization.
"""

import uuid
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from backend.app.db.models import ProcurementInventory, ProcurementPurchaseOrder
from backend.app.services.agent_event_bus import AgentEventBus

logger = logging.getLogger("ProcurementAgent")

class ProcurementAgent:
    @staticmethod
    def audit_inventory(db: Session) -> Dict[str, Any]:
        """
        Scans all 100-bed facility inventory items.
        Flags critical, low-stock, and expiring items.
        Automatically prepares purchase order drafts for items below reorder threshold.
        """
        items = db.scalars(select(ProcurementInventory)).all()
        total_items = len(items)

        low_stock_items = []
        critical_items = []
        expiring_items = []

        now_date = date.today()
        expiry_cutoff = now_date + timedelta(days=90)  # Expiring in next 3 months

        for itm in items:
            # Check stock
            if itm.current_stock <= (itm.reorder_threshold * 0.35):
                itm.status = "critical"
                critical_items.append(itm)
            elif itm.current_stock <= itm.reorder_threshold:
                itm.status = "low_stock"
                low_stock_items.append(itm)
            else:
                itm.status = "in_stock"

            # Check expiry
            if itm.expiry_date and itm.expiry_date <= expiry_cutoff:
                expiring_items.append(itm)

        db.commit()

        # Check existing pending drafts to avoid duplicate PO generation
        existing_pos = db.scalars(
            select(ProcurementPurchaseOrder).where(
                ProcurementPurchaseOrder.status.in_(["draft_pending_authorization", "approved", "ordered"])
            )
        ).all()
        existing_item_ids = {po.item_id for po in existing_pos}

        new_drafts_created = []
        now_utc = datetime.now(timezone.utc)
        for itm in critical_items + low_stock_items:
            if itm.item_id not in existing_item_ids:
                po_id = f"PO-{now_date.year}-{uuid.uuid4().hex[:6].upper()}"
                qty = itm.reorder_quantity
                cost = round(qty * itm.unit_price, 2)
                notes = (
                    f"CRITICAL SHORTAGE: Stock is at {itm.current_stock} {itm.unit} (Threshold: {itm.reorder_threshold}). Immediate procurement advised."
                    if itm.status == "critical" else
                    f"LOW STOCK: Current stock ({itm.current_stock} {itm.unit}) is below reorder threshold ({itm.reorder_threshold} {itm.unit})."
                )
                new_po = ProcurementPurchaseOrder(
                    po_id=po_id,
                    item_id=itm.item_id,
                    quantity=qty,
                    estimated_cost=cost,
                    supplier_name=itm.supplier_name,
                    generated_by="procurement_agent",
                    status="draft_pending_authorization",
                    approval_notes=notes,
                    created_at=now_utc
                )
                db.add(new_po)
                new_drafts_created.append(po_id)

                # Emit event requiring management authorization
                AgentEventBus.emit(
                    source_agent="procurement_agent",
                    event_type="PURCHASE_ORDER_DRAFTED",
                    payload={
                        "po_id": po_id,
                        "item_name": itm.name,
                        "quantity": qty,
                        "unit": itm.unit,
                        "estimated_cost": cost,
                        "supplier": itm.supplier_name,
                        "reason": notes
                    },
                    target_agent="management_dashboard",
                    requires_human_approval=True,
                    db=db
                )

        if new_drafts_created:
            db.commit()

        return {
            "total_inventory_items": total_items,
            "critical_count": len(critical_items),
            "low_stock_count": len(low_stock_items),
            "expiring_count": len(expiring_items),
            "new_po_drafts_generated": new_drafts_created,
            "critical_items": [
                {"item_id": i.item_id, "name": i.name, "current_stock": i.current_stock, "unit": i.unit, "threshold": i.reorder_threshold}
                for i in critical_items
            ],
            "low_stock_items": [
                {"item_id": i.item_id, "name": i.name, "current_stock": i.current_stock, "unit": i.unit, "threshold": i.reorder_threshold}
                for i in low_stock_items
            ],
            "expiring_items": [
                {"item_id": i.item_id, "name": i.name, "expiry_date": str(i.expiry_date), "batch": i.batch_number}
                for i in expiring_items
            ]
        }

    @staticmethod
    def authorize_purchase_order(
        po_id: str,
        action: str,  # "approve" or "reject"
        approved_by: str,
        notes: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Human approval workflow for AI purchase orders."""
        po = db.scalar(select(ProcurementPurchaseOrder).where(ProcurementPurchaseOrder.po_id == po_id))
        if not po:
            raise ValueError(f"Purchase order {po_id} not found")

        po.status = "approved" if action == "approve" else "rejected"
        po.approved_by = approved_by
        po.approval_notes = f"{action.upper()}: {notes or 'Authorized by hospital management'}"
        db.commit()

        AgentEventBus.emit(
            source_agent="procurement_agent",
            event_type="PURCHASE_ORDER_STATUS_CHANGED",
            payload={
                "po_id": po_id,
                "status": po.status,
                "approved_by": approved_by,
                "notes": po.approval_notes
            },
            target_agent="management_dashboard",
            requires_human_approval=False,
            db=db
        )

        return {
            "po_id": po.po_id,
            "status": po.status,
            "approved_by": po.approved_by,
            "notes": po.approval_notes
        }
