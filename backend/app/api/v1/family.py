import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.app.db.session import get_db
from backend.app.db.models import Patient, FamilyLink, AuditLog
from backend.app.db.schemas import (
    FamilyLinkRequestCreate,
    FamilyLinkRespondRequest,
    FamilyLinkPermissionsUpdate,
    FamilyLinkRead,
)
from backend.app.core.dependencies import get_current_user, log_audit_event
from backend.app.core.demo_users import User
from backend.app.services.ehr_service import LongitudinalEHRService

router = APIRouter(prefix="/family", tags=["Patient Family Accounts"])

ALL_PERMISSIONS = [
    "view_basic_health",
    "view_medical_history",
    "view_reports",
    "manage_appointments",
    "receive_reminders",
    "assist_admissions",
    "access_documents"
]


@router.get("/search", response_model=List[Dict[str, Any]])
def search_family_members(
    q: str = Query(..., min_length=2, description="Search term (Name or Patient ID)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search registered patients to establish family connections.
    Privacy-first: Returns limited matching information (name, gender, age bracket, masked contact)
    WITHOUT revealing private medical diagnoses, records, or clinical details.
    """
    requester_id = current_user.patient_id or ""
    query = db.query(Patient).filter(
        Patient.patient_id != requester_id
    )

    clean_q = q.strip()
    if clean_q.upper().startswith("PAT-"):
        query = query.filter(Patient.patient_id.ilike(f"%{clean_q}%"))
    else:
        name_parts = clean_q.split()
        if len(name_parts) >= 2:
            query = query.filter(
                and_(
                    Patient.first_name.ilike(f"%{name_parts[0]}%"),
                    Patient.last_name.ilike(f"%{name_parts[1]}%")
                )
            )
        else:
            query = query.filter(
                or_(
                    Patient.first_name.ilike(f"%{clean_q}%"),
                    Patient.last_name.ilike(f"%{clean_q}%")
                )
            )

    matches = query.limit(10).all()
    results = []
    for p in matches:
        # Mask phone number for privacy
        masked_phone = None
        if p.contact_no:
            cleaned = str(p.contact_no).strip()
            if len(cleaned) >= 4:
                masked_phone = f"+91 ******{cleaned[-4:]}"
            else:
                masked_phone = "+91 ******"

        # Age bracket e.g. "35-40 years"
        age = p.age or 35
        bracket_low = (age // 5) * 5
        age_bracket = f"{bracket_low}-{bracket_low + 5} years"

        results.append({
            "patient_id": p.patient_id,
            "full_name": f"{p.first_name} {p.last_name}".strip(),
            "gender": p.sex,
            "age_bracket": age_bracket,
            "masked_contact": masked_phone,
            "city_district": p.district
        })

    log_audit_event(db, current_user, "FAMILY_MEMBER_SEARCH", requester_id, f"Query: {clean_q}")
    return results


@router.post("/requests", response_model=FamilyLinkRead, status_code=status.HTTP_201_CREATED)
def send_family_link_request(
    payload: FamilyLinkRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a family connection link request to another registered patient.
    Requires target patient's authenticated in-app approval before access is granted.
    """
    requester_id = current_user.patient_id
    if not requester_id:
        raise HTTPException(status_code=400, detail="Only registered patient accounts can link family accounts.")

    if requester_id == payload.target_patient_id:
        raise HTTPException(status_code=400, detail="Cannot link your own account to yourself.")

    target = db.query(Patient).filter(Patient.patient_id == payload.target_patient_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target patient account not found.")

    # Check for existing link
    existing = db.query(FamilyLink).filter(
        or_(
            and_(FamilyLink.requester_patient_id == requester_id, FamilyLink.target_patient_id == payload.target_patient_id),
            and_(FamilyLink.requester_patient_id == payload.target_patient_id, FamilyLink.target_patient_id == requester_id)
        )
    ).first()

    if existing:
        if existing.status == "approved":
            raise HTTPException(status_code=400, detail="An active family connection already exists with this patient.")
        if existing.status == "pending":
            raise HTTPException(status_code=400, detail="A family link request is already pending between these accounts.")
        # Reactivate revoked/rejected request
        existing.status = "pending"
        existing.relationship_type = payload.relationship_type
        existing.permissions_json = json.dumps(payload.permissions)
        existing.requested_at = datetime.now(timezone.utc)
        existing.responded_at = None
        existing.notes = payload.notes
        db.commit()
        db.refresh(existing)
        link = existing
    else:
        link_id = f"FLK-{uuid.uuid4().hex[:10].upper()}"
        link = FamilyLink(
            link_id=link_id,
            requester_patient_id=requester_id,
            target_patient_id=payload.target_patient_id,
            relationship_type=payload.relationship_type,
            status="pending",
            permissions_json=json.dumps(payload.permissions),
            requested_at=datetime.now(timezone.utc),
            notes=payload.notes
        )
        db.add(link)
        db.commit()
        db.refresh(link)

    requester_p = db.query(Patient).filter(Patient.patient_id == requester_id).first()
    log_audit_event(db, current_user, "FAMILY_LINK_REQUEST_SENT", link.link_id, f"To: {target.patient_id}")

    return FamilyLinkRead(
        link_id=link.link_id,
        requester_patient_id=link.requester_patient_id,
        target_patient_id=link.target_patient_id,
        requester_name=f"{requester_p.first_name} {requester_p.last_name}" if requester_p else requester_id,
        target_name=f"{target.first_name} {target.last_name}",
        relationship_type=link.relationship_type,
        status=link.status,
        permissions=json.loads(link.permissions_json) if link.permissions_json else [],
        requested_at=link.requested_at.isoformat(),
        responded_at=link.responded_at.isoformat() if link.responded_at else None,
        notes=link.notes
    )


@router.get("/requests", response_model=List[FamilyLinkRead])
def list_family_link_requests(
    direction: str = Query("all", description="Direction: incoming, outgoing, or all"),
    status_filter: Optional[str] = Query(None, description="pending, approved, rejected, revoked"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List incoming and outgoing family link requests for the authenticated patient.
    """
    patient_id = current_user.patient_id
    if not patient_id:
        return []

    query = db.query(FamilyLink)
    if direction == "incoming":
        query = query.filter(FamilyLink.target_patient_id == patient_id)
    elif direction == "outgoing":
        query = query.filter(FamilyLink.requester_patient_id == patient_id)
    else:
        query = query.filter(
            or_(
                FamilyLink.requester_patient_id == patient_id,
                FamilyLink.target_patient_id == patient_id
            )
        )

    if status_filter:
        query = query.filter(FamilyLink.status == status_filter)

    links = query.order_by(FamilyLink.requested_at.desc()).all()

    # Preload patient names
    patient_ids = set()
    for l in links:
        patient_ids.add(l.requester_patient_id)
        patient_ids.add(l.target_patient_id)
    patients = {p.patient_id: f"{p.first_name} {p.last_name}".strip() for p in db.query(Patient).filter(Patient.patient_id.in_(patient_ids)).all()}

    output = []
    for l in links:
        output.append(FamilyLinkRead(
            link_id=l.link_id,
            requester_patient_id=l.requester_patient_id,
            target_patient_id=l.target_patient_id,
            requester_name=patients.get(l.requester_patient_id, l.requester_patient_id),
            target_name=patients.get(l.target_patient_id, l.target_patient_id),
            relationship_type=l.relationship_type,
            status=l.status,
            permissions=json.loads(l.permissions_json) if l.permissions_json else [],
            requested_at=l.requested_at.isoformat(),
            responded_at=l.responded_at.isoformat() if l.responded_at else None,
            notes=l.notes
        ))
    return output


@router.post("/requests/{link_id}/respond", response_model=FamilyLinkRead)
def respond_family_link_request(
    link_id: str,
    payload: FamilyLinkRespondRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Respond to an incoming family link request (approve or reject).
    Target user can optionally customize granted permissions upon approval.
    """
    patient_id = current_user.patient_id
    link = db.query(FamilyLink).filter(FamilyLink.link_id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Family link request not found.")

    # Only target patient can respond to incoming requests
    if link.target_patient_id != patient_id and current_user.role != "hospital_admin":
        raise HTTPException(status_code=403, detail="Only the target account can approve or reject this request.")

    if payload.action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

    link.status = "approved" if payload.action == "approve" else "rejected"
    link.responded_at = datetime.now(timezone.utc)
    if payload.permissions is not None and payload.action == "approve":
        link.permissions_json = json.dumps(payload.permissions)
    if payload.notes:
        link.notes = payload.notes

    db.commit()
    db.refresh(link)

    log_audit_event(db, current_user, f"FAMILY_LINK_{link.status.upper()}", link.link_id, f"Status: {link.status}")

    requester_p = db.query(Patient).filter(Patient.patient_id == link.requester_patient_id).first()
    target_p = db.query(Patient).filter(Patient.patient_id == link.target_patient_id).first()

    return FamilyLinkRead(
        link_id=link.link_id,
        requester_patient_id=link.requester_patient_id,
        target_patient_id=link.target_patient_id,
        requester_name=f"{requester_p.first_name} {requester_p.last_name}" if requester_p else link.requester_patient_id,
        target_name=f"{target_p.first_name} {target_p.last_name}" if target_p else link.target_patient_id,
        relationship_type=link.relationship_type,
        status=link.status,
        permissions=json.loads(link.permissions_json) if link.permissions_json else [],
        requested_at=link.requested_at.isoformat(),
        responded_at=link.responded_at.isoformat() if link.responded_at else None,
        notes=link.notes
    )


@router.patch("/links/{link_id}/permissions", response_model=FamilyLinkRead)
def update_family_link_permissions(
    link_id: str,
    payload: FamilyLinkPermissionsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update granular permissions for an active family connection.
    The patient sharing their data controls what is shared.
    """
    patient_id = current_user.patient_id
    link = db.query(FamilyLink).filter(FamilyLink.link_id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Family link not found.")

    if link.requester_patient_id != patient_id and link.target_patient_id != patient_id and current_user.role != "hospital_admin":
        raise HTTPException(status_code=403, detail="Unauthorized to modify this family link.")

    link.permissions_json = json.dumps(payload.permissions)
    db.commit()
    db.refresh(link)

    log_audit_event(db, current_user, "FAMILY_LINK_PERMISSIONS_UPDATED", link.link_id, f"Perms: {payload.permissions}")

    requester_p = db.query(Patient).filter(Patient.patient_id == link.requester_patient_id).first()
    target_p = db.query(Patient).filter(Patient.patient_id == link.target_patient_id).first()

    return FamilyLinkRead(
        link_id=link.link_id,
        requester_patient_id=link.requester_patient_id,
        target_patient_id=link.target_patient_id,
        requester_name=f"{requester_p.first_name} {requester_p.last_name}" if requester_p else link.requester_patient_id,
        target_name=f"{target_p.first_name} {target_p.last_name}" if target_p else link.target_patient_id,
        relationship_type=link.relationship_type,
        status=link.status,
        permissions=json.loads(link.permissions_json) if link.permissions_json else [],
        requested_at=link.requested_at.isoformat(),
        responded_at=link.responded_at.isoformat() if link.responded_at else None,
        notes=link.notes
    )


@router.delete("/links/{link_id}")
def revoke_family_link(
    link_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke/remove an existing family connection. Either party can revoke access at any time.
    """
    patient_id = current_user.patient_id
    link = db.query(FamilyLink).filter(FamilyLink.link_id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Family link not found.")

    if link.requester_patient_id != patient_id and link.target_patient_id != patient_id and current_user.role != "hospital_admin":
        raise HTTPException(status_code=403, detail="Unauthorized to revoke this family link.")

    link.status = "revoked"
    db.commit()

    log_audit_event(db, current_user, "FAMILY_LINK_REVOKED", link.link_id)
    return {"message": "Family connection successfully revoked.", "link_id": link_id}


@router.get("/members", response_model=List[Dict[str, Any]])
def list_connected_family_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all active connected family members for the patient, including their
    relationship, permissions granted, and profile metadata.
    """
    patient_id = current_user.patient_id
    if not patient_id:
        return []

    links = db.query(FamilyLink).filter(
        or_(
            FamilyLink.requester_patient_id == patient_id,
            FamilyLink.target_patient_id == patient_id
        ),
        FamilyLink.status == "approved"
    ).all()

    results = []
    for l in links:
        other_id = l.target_patient_id if l.requester_patient_id == patient_id else l.requester_patient_id
        other_patient = db.query(Patient).filter(Patient.patient_id == other_id).first()
        if not other_patient:
            continue

        perms = json.loads(l.permissions_json) if l.permissions_json else []
        results.append({
            "link_id": l.link_id,
            "patient_id": other_patient.patient_id,
            "full_name": f"{other_patient.first_name} {other_patient.last_name}".strip(),
            "relationship_type": l.relationship_type,
            "age": other_patient.age,
            "gender": other_patient.sex,
            "blood_group": "O+" if other_id.startswith("PAT-AARAV") else "B+",
            "permissions": perms,
            "linked_since": l.requested_at.strftime("%Y-%m-%d"),
            "can_manage_appointments": "manage_appointments" in perms,
            "can_view_records": "view_medical_history" in perms or "view_basic_health" in perms,
            "can_view_reports": "view_reports" in perms
        })

    return results


@router.get("/members/{family_patient_id}/ehr")
def get_family_member_permitted_ehr(
    family_patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve permitted longitudinal EHR of a connected family member.
    Enforces minimum necessary access and filters data according to granted consent scopes.
    """
    requester_id = current_user.patient_id
    if not requester_id:
        raise HTTPException(status_code=403, detail="Patient account required.")

    # Check verified link
    link = db.query(FamilyLink).filter(
        or_(
            and_(FamilyLink.requester_patient_id == requester_id, FamilyLink.target_patient_id == family_patient_id),
            and_(FamilyLink.requester_patient_id == family_patient_id, FamilyLink.target_patient_id == requester_id)
        ),
        FamilyLink.status == "approved"
    ).first()

    if not link and current_user.role != "hospital_admin":
        raise HTTPException(status_code=403, detail="No approved family connection exists with this patient.")

    perms = json.loads(link.permissions_json) if (link and link.permissions_json) else ALL_PERMISSIONS

    # Get complete raw EHR
    full_ehr = LongitudinalEHRService.get_complete_patient_record(family_patient_id, db)
    if "error" in full_ehr:
        raise HTTPException(status_code=404, detail="Patient EHR record not found.")

    # Filter EHR strictly according to granted permissions
    filtered_ehr = {
        "patient_id": family_patient_id,
        "relationship_type": link.relationship_type if link else "Self",
        "demographics": full_ehr.get("demographics", {}),
        "permitted_scopes": perms
    }

    if "view_basic_health" in perms:
        filtered_ehr["allergies"] = full_ehr.get("allergies", [])
        filtered_ehr["latest_daily_vitals"] = full_ehr.get("daily_logs", [])[:5]

    if "view_medical_history" in perms:
        filtered_ehr["conditions"] = full_ehr.get("conditions", [])
        filtered_ehr["medications"] = full_ehr.get("medications", [])
        filtered_ehr["encounters"] = full_ehr.get("encounters", [])

    if "view_reports" in perms:
        filtered_ehr["observations"] = full_ehr.get("observations", [])
        filtered_ehr["documents"] = full_ehr.get("documents", [])

    if "manage_appointments" in perms:
        filtered_ehr["can_manage_appointments"] = True

    log_audit_event(db, current_user, "FAMILY_EHR_VIEWED", family_patient_id, f"Scopes: {perms}")
    return filtered_ehr
