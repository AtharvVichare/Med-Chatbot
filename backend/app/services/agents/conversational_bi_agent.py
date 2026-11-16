"""
Conversational BI Agent for Aarogya-Drishti HMS.
Converts management's natural-language questions into safe, validated database queries
and displays interactive analytics, summaries, and chart visualizations.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.app.db.models import (
    BedRegistry,
    ProcurementInventory,
    BillingInvoice,
    AppointmentBooking,
    AdmissionRequest,
    Patient
)
from backend.app.services.agents.scheduling_agent import SchedulingAgent
from backend.app.services.agents.procurement_agent import ProcurementAgent
from backend.app.services.agents.billing_rcm_agent import BillingRCMAgent
from backend.app.services.agent_event_bus import AgentEventBus

logger = logging.getLogger("ConversationalBIAgent")

class ConversationalBIAgent:
    @staticmethod
    def query(natural_query: str, db: Session) -> Dict[str, Any]:
        """
        Interprets natural language questions from hospital leadership,
        executes safe analytical computations, and formats structured charts and text.
        """
        q_low = natural_query.lower()

        # 1. Bed Occupancy & Capacity Inquiries
        if any(k in q_low for k in ["bed", "occupancy", "ward", "icu capacity", "available bed", "capacity"]):
            overview = SchedulingAgent.get_bed_overview(db)
            total = overview["total_beds"]
            occ = overview["occupied_beds"]
            avail = overview["available_beds"]
            rate = overview["occupancy_rate"]

            ward_labels = [w["ward"] for w in overview["wards"]]
            ward_occupied = [w["occupied"] for w in overview["wards"]]
            ward_available = [w["available"] for w in overview["wards"]]

            answer = (
                f"### Current Hospital Bed Occupancy & Capacity (100-Bed Facility)\n\n"
                f"- **Overall Occupancy:** **{rate}%** ({occ}/{total} beds occupied)\n"
                f"- **Available Beds:** **{avail}** beds ready for immediate admission\n"
                f"- **Under Cleaning/Maintenance:** **{overview['cleaning_beds'] + overview['maintenance_beds']}** beds\n\n"
                f"**Ward Status Summary:**\n"
                + "\n".join([f"- **{w['ward']}:** {w['occupied']}/{w['total']} occupied ({w['available']} available)" for w in overview["wards"]])
            )

            chart = {
                "type": "bar",
                "title": "Ward-wise Bed Occupancy",
                "labels": ward_labels,
                "series": [
                    {"name": "Occupied", "data": ward_occupied},
                    {"name": "Available", "data": ward_available}
                ]
            }

            return {
                "query": natural_query,
                "domain": "bed_management",
                "summary": answer,
                "chart": chart,
                "metrics": {
                    "total_beds": total,
                    "occupied_beds": occ,
                    "available_beds": avail,
                    "occupancy_rate": rate
                }
            }

        # 2. Procurement & Medicine Inventory Inquiries
        elif any(k in q_low for k in ["inventory", "medicine", "stock", "running low", "shortage", "procurement", "supply", "expiry"]):
            audit = ProcurementAgent.audit_inventory(db)
            crit = audit["critical_items"]
            low = audit["low_stock_items"]
            exp = audit["expiring_items"]

            answer = (
                f"### Pharmacy & Procurement Inventory Status\n\n"
                f"- **Critical Shortages:** **{len(crit)}** items requiring urgent reorder\n"
                f"- **Low Stock Warnings:** **{len(low)}** items below threshold\n"
                f"- **Expiring Batches (90 days):** **{len(exp)}** items\n\n"
            )
            if crit:
                answer += "**Critical Items (Immediate Action):**\n" + "\n".join([f"- 🚨 **{i['name']}**: Only {i['current_stock']} {i['unit']} left (Threshold: {i['threshold']})" for i in crit]) + "\n\n"
            if low:
                answer += "**Low Stock Items:**\n" + "\n".join([f"- ⚠️ **{i['name']}**: {i['current_stock']} {i['unit']} (Threshold: {i['threshold']})" for i in low])

            chart = {
                "type": "pie",
                "title": "Inventory Health Status",
                "labels": ["In Stock", "Low Stock", "Critical Shortage"],
                "data": [
                    audit["total_inventory_items"] - len(crit) - len(low),
                    len(low),
                    len(crit)
                ]
            }

            return {
                "query": natural_query,
                "domain": "procurement",
                "summary": answer,
                "chart": chart,
                "metrics": {
                    "critical_count": len(crit),
                    "low_stock_count": len(low),
                    "expiring_count": len(exp)
                }
            }

        # 3. Revenue & Financial Analytics
        elif any(k in q_low for k in ["revenue", "billing", "finance", "money", "billed", "collection", "payment"]):
            fin = BillingRCMAgent.get_revenue_cycle_summary(db)

            answer = (
                f"### Revenue Cycle & Financial Health\n\n"
                f"- **Total Billed Revenue:** **₹{fin['total_billed']:,.2f}**\n"
                f"- **Total Collected:** **₹{fin['total_collected']:,.2f}** ({fin['collection_rate']}% collection rate)\n"
                f"- **Insurance Claims:** **₹{fin['total_insurance_claimed']:,.2f}**\n"
                f"- **Pending Patient Balances:** **₹{fin['pending_collections']:,.2f}**\n"
            )

            chart = {
                "type": "bar",
                "title": "Revenue Breakdown (INR)",
                "labels": ["Total Billed", "Collected", "Insurance Claims", "Pending"],
                "series": [
                    {"name": "Amount (₹)", "data": [fin["total_billed"], fin["total_collected"], fin["total_insurance_claimed"], fin["pending_collections"]]}
                ]
            }

            return {
                "query": natural_query,
                "domain": "finance",
                "summary": answer,
                "chart": chart,
                "metrics": fin
            }

        # 4. Appointment & Outpatient Workload
        elif any(k in q_low for k in ["appointment", "consultation", "opd", "doctor schedule", "bookings"]):
            appts = db.scalars(select(AppointmentBooking)).all()
            total_appts = len(appts)
            confirmed = sum(1 for a in appts if a.status == "confirmed")
            completed = sum(1 for a in appts if a.status == "completed")
            cancelled = sum(1 for a in appts if a.status == "cancelled")

            dept_counts = {}
            for a in appts:
                dept_counts[a.department] = dept_counts.get(a.department, 0) + 1

            answer = (
                f"### Appointment & OPD Consultations Overview\n\n"
                f"- **Total Booked Consultations:** **{total_appts}**\n"
                f"- **Upcoming Confirmed:** **{confirmed}**\n"
                f"- **Completed Consultations:** **{completed}**\n"
                f"- **Cancelled:** **{cancelled}**\n\n"
                f"**Specialty Demand Breakdown:**\n"
                + "\n".join([f"- **{dept}:** {cnt} appointments" for dept, cnt in dept_counts.items()])
            )

            chart = {
                "type": "bar",
                "title": "Appointments by Specialty",
                "labels": list(dept_counts.keys()),
                "series": [
                    {"name": "Appointments", "data": list(dept_counts.values())}
                ]
            }

            return {
                "query": natural_query,
                "domain": "appointments",
                "summary": answer,
                "chart": chart,
                "metrics": {
                    "total_appointments": total_appts,
                    "confirmed": confirmed,
                    "completed": completed
                }
            }

        # 5. General Hospital Summary
        else:
            bed_ov = SchedulingAgent.get_bed_overview(db)
            inv_ov = ProcurementAgent.audit_inventory(db)
            fin_ov = BillingRCMAgent.get_revenue_cycle_summary(db)

            answer = (
                f"### Aarogya-Drishti 100-Bed Hospital Operational Summary\n\n"
                f"- **Inpatient Capacity:** **{bed_ov['occupancy_rate']}%** occupancy ({bed_ov['occupied_beds']}/100 beds occupied; {bed_ov['available_beds']} available).\n"
                f"- **Pharmacy / Procurement:** **{inv_ov['critical_count']}** critical shortages, **{inv_ov['low_stock_count']}** low-stock items.\n"
                f"- **Financial Health:** **₹{fin_ov['total_collected']:,.2f}** collected out of **₹{fin_ov['total_billed']:,.2f}** billed.\n"
                f"- **Multi-Agent Network:** 6 Autonomous AI Agents active on Inter-Agent Event Bus.\n\n"
                f"*Tip: You can ask specific questions like 'What is our bed occupancy?', 'Show medicines running low', or 'What is our billing status?'*"
            )

            return {
                "query": natural_query,
                "domain": "hospital_overview",
                "summary": answer,
                "chart": None,
                "metrics": {
                    "occupancy_rate": bed_ov["occupancy_rate"],
                    "critical_inventory": inv_ov["critical_count"],
                    "total_revenue": fin_ov["total_billed"]
                }
            }
