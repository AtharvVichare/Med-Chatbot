import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.core.security import decode_access_token
from backend.app.core.demo_users import DEMO_USERS_DB, User
from backend.app.db.models import AuditLog

security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not recognized in system",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Check in DEMO_USERS_DB first
    if username in DEMO_USERS_DB:
        return DEMO_USERS_DB[username]

    # 2. Check in dynamic database UserAccount
    from backend.app.db.models import UserAccount
    db_user = db.scalar(select(UserAccount).where((UserAccount.username == username) | (UserAccount.email == username)))
    if db_user:
        return User(
            username=db_user.username,
            password_hash=db_user.password_hash,
            role=db_user.role,
            patient_id=db_user.patient_id,
            full_name=db_user.full_name,
            facility="Aarogya Patient Portal"
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User account not found or deactivated",
        headers={"WWW-Authenticate": "Bearer"},
    )

def log_audit_event(
    db: Session,
    user: User,
    action: str,
    record_id: str,
    record_type: str = "patient_record",
    facility: Optional[str] = None
):
    try:
        log_entry = AuditLog(
            log_id=f"AUD-{uuid.uuid4().hex[:10].upper()}",
            user_id=user.username,
            action=action,
            record_id=record_id,
            record_type=record_type,
            facility=facility or user.facility or "Unknown",
            timestamp=datetime.now(timezone.utc),
            is_synthetic=True
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()

def verify_patient_access(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Enforces Strict Patient-Level Authorization:
    - Public Health Analyst: ALWAYS 403 Forbidden on individual identifiable patient records.
    - Patient: Can ONLY access their own patient_id.
    - Doctor: Can ONLY access explicitly assigned patients.
    - Hospital Admin: Authorized.
    Logs all authorized and denied attempts in audit_logs.
    """
    # 1. Public Health Analyst restriction
    if current_user.role == "public_health_analyst":
        log_audit_event(db, current_user, "ACCESS_DENIED_ANALYST_RESTRICTION", patient_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public health analysts are prohibited from accessing identifiable patient records."
        )

    # 2. Patient restriction
    if current_user.role == "patient":
        if current_user.patient_id != patient_id:
            log_audit_event(db, current_user, "ACCESS_DENIED_CROSS_PATIENT", patient_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You are only authorized to view your own patient record ({current_user.patient_id})."
            )

    # 3. Doctor restriction (explicit assignment required)
    elif current_user.role == "doctor":
        if patient_id not in current_user.assigned_patients:
            log_audit_event(db, current_user, "ACCESS_DENIED_UNASSIGNED_PATIENT", patient_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Dr. {current_user.full_name} is not assigned to patient {patient_id}."
            )

    # 4. Authorized Access
    log_audit_event(db, current_user, "EHR_PATIENT_ACCESS_AUTHORIZED", patient_id)
    return current_user

