"""
Demo Synthetic Users Setup for Aarogya-Drishti EHR
Roles Supported:
1. Patient ('patient'): Can access ONLY their own record.
2. Doctor ('doctor'): Can access ONLY explicitly assigned synthetic patients.
3. Hospital Administrator ('hospital_admin'): Can access all patient records & clinical services in facility.
4. Public Health Analyst ('public_health_analyst'): Can access aggregate analytics; CANNOT access identifiable patient records.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel
from backend.app.core.security import hash_password, verify_password

class User(BaseModel):
    username: str
    password_hash: str
    role: str
    patient_id: Optional[str] = None  # For Patient role
    assigned_patients: List[str] = []  # For Doctor role
    full_name: str
    facility: Optional[str] = None

# Pre-hashed passwords for test/demo initialization
DEMO_PASSWORD = "DemoPassword123!"

DEMO_USERS_DB: Dict[str, User] = {
    # 1. Patient User: Can view PAT-00001
    "patient_user": User(
        username="patient_user",
        password_hash=hash_password(DEMO_PASSWORD),
        role="patient",
        patient_id="PAT-00001",
        full_name="Isha Nair",
        facility="Seth GS Medical College & KEM Hospital"
    ),
    # 2. Doctor User: Assigned explicitly to synthetic patients
    "doctor_user": User(
        username="doctor_user",
        password_hash=hash_password(DEMO_PASSWORD),
        role="doctor",
        assigned_patients=["PAT-00001", "PAT-00002", "PAT-AARAV-001", "PAT-PRIYA-002", "PAT-ROHAN-003", "PAT-SUNITA-004"],
        full_name="Dr. Priya Deshmukh",
        facility="Seth GS Medical College & KEM Hospital"
    ),
    # 3. Hospital Administrator: Facility wide access
    "admin_user": User(
        username="admin_user",
        password_hash=hash_password(DEMO_PASSWORD),
        role="hospital_admin",
        full_name="Dr. Rajesh Deshmukh",
        facility="Seth GS Medical College & KEM Hospital"
    ),
    # 4. Nurse User: Clinical shift feed, ward vitals, bed allocation
    "nurse_user": User(
        username="nurse_user",
        password_hash=hash_password(DEMO_PASSWORD),
        role="nurse",
        assigned_patients=["PAT-00001", "PAT-00002", "PAT-00003", "PAT-AARAV-001", "PAT-PRIYA-002", "PAT-ROHAN-003", "PAT-SUNITA-004"],
        full_name="Nurse Anjali Sharma",
        facility="Seth GS Medical College & KEM Hospital"
    ),
    # 5. Public Health Analyst: Strictly forbidden from identifiable patient records
    "analyst_user": User(
        username="analyst_user",
        password_hash=hash_password(DEMO_PASSWORD),
        role="public_health_analyst",
        full_name="Public Health Epidemiologist",
        facility="National Health Observatory [SYNTHETIC]"
    ),
    # 6. Primary Patient: Aarav Mehta (Demonstration Family Account)
    "aarav_mehta": User(
        username="aarav_mehta",
        password_hash=hash_password(DEMO_PASSWORD),
        role="patient",
        patient_id="PAT-AARAV-001",
        full_name="Aarav Mehta",
        facility="Seth GS Medical College & KEM Hospital [SYNTHETIC]"
    ),
    # 7. Spouse: Priya Mehta
    "priya_mehta": User(
        username="priya_mehta",
        password_hash=hash_password(DEMO_PASSWORD),
        role="patient",
        patient_id="PAT-PRIYA-002",
        full_name="Priya Mehta",
        facility="Seth GS Medical College & KEM Hospital [SYNTHETIC]"
    ),
    # 8. Brother: Rohan Mehta
    "rohan_mehta": User(
        username="rohan_mehta",
        password_hash=hash_password(DEMO_PASSWORD),
        role="patient",
        patient_id="PAT-ROHAN-003",
        full_name="Rohan Mehta",
        facility="Seth GS Medical College & KEM Hospital [SYNTHETIC]"
    ),
    # 9. Mother: Sunita Mehta
    "sunita_mehta": User(
        username="sunita_mehta",
        password_hash=hash_password(DEMO_PASSWORD),
        role="patient",
        patient_id="PAT-SUNITA-004",
        full_name="Sunita Mehta",
        facility="Seth GS Medical College & KEM Hospital [SYNTHETIC]"
    )
}

def authenticate_user(username: str, password: str) -> Optional[User]:
    user = DEMO_USERS_DB.get(username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

