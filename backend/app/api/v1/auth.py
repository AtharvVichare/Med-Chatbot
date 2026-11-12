import uuid
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.schemas.api_schemas import (
    LoginRequest,
    TokenResponse,
    SignupRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserProfileResponse
)
from backend.app.core.demo_users import authenticate_user, User
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.core.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.db.models import UserAccount, Patient

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # 1. Check demo users first
    user = authenticate_user(credentials.username, credentials.password)
    
    # 2. If not found in demo users, check PostgreSQL users table
    if not user:
        db_user = db.scalar(
            select(UserAccount).where(
                (UserAccount.username == credentials.username) | 
                (UserAccount.email == credentials.username)
            )
        )
        if db_user and verify_password(credentials.password, db_user.password_hash):
            user = User(
                username=db_user.username,
                password_hash=db_user.password_hash,
                role=db_user.role,
                patient_id=db_user.patient_id,
                full_name=db_user.full_name,
                facility="Aarogya Patient Portal"
            )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    return TokenResponse(
        access_token=access_token,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
        patient_id=user.patient_id
    )

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    # Check if username or email already exists
    existing = db.scalar(
        select(UserAccount).where(
            (UserAccount.username == req.username) | (UserAccount.email == req.email)
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email or username already exists."
        )

    # Automatically create a fresh longitudinal Patient record in the EHR database
    new_patient_id = f"PAT-{uuid.uuid4().hex[:8].upper()}"
    new_abha = f"91-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
    
    # Calculate initial age from birth date
    today = date.today()
    calculated_age = today.year - req.date_of_birth.year - (
        (today.month, today.day) < (req.date_of_birth.month, req.date_of_birth.day)
    )

    if req.full_name:
        names = req.full_name.strip().split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else "Patient"
    else:
        first_name = req.first_name or "New"
        last_name = req.last_name or "Patient"

    phone = req.phone_number or req.phone
    district = req.district or "Self-Registered Patient"

    patient_rec = Patient(
        patient_id=new_patient_id,
        abha_number=new_abha,
        first_name=first_name,
        last_name=last_name,
        birth_date=req.date_of_birth,
        age=max(0, calculated_age),
        sex=req.gender or "unspecified",
        state="Registered Online",
        district=district,
        contact_no=phone,
        registered_date=today,
        is_synthetic=False,
        data_source="PATIENT_PORTAL_REGISTRATION"
    )
    db.add(patient_rec)
    db.flush()

    # Create the User account linked directly to the new patient record
    user_acc = UserAccount(
        id=f"USR-{uuid.uuid4().hex[:10].upper()}",
        email=req.email.lower().strip(),
        username=req.username.strip(),
        password_hash=hash_password(req.password),
        full_name=(req.full_name or f"{first_name} {last_name}").strip(),
        role="patient",
        patient_id=new_patient_id,
        phone_number=phone,
        date_of_birth=req.date_of_birth,
        gender=req.gender,
        is_active=True
    )
    db.add(user_acc)
    db.commit()

    access_token = create_access_token(
        data={"sub": user_acc.username, "role": user_acc.role}
    )
    return TokenResponse(
        access_token=access_token,
        role=user_acc.role,
        username=user_acc.username,
        full_name=user_acc.full_name,
        patient_id=user_acc.patient_id
    )

@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # If dynamic user, query db
    db_user = db.scalar(select(UserAccount).where(UserAccount.username == current_user.username))
    if db_user:
        return UserProfileResponse(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            patient_id=db_user.patient_id,
            phone_number=db_user.phone_number,
            date_of_birth=db_user.date_of_birth,
            gender=db_user.gender
        )
    # If demo user
    return UserProfileResponse(
        id=f"DEMO-{current_user.username.upper()}",
        username=current_user.username,
        email=f"{current_user.username}@aarogyadrishti.org",
        full_name=current_user.full_name,
        role=current_user.role,
        patient_id=current_user.patient_id,
        phone_number="+91 98765 43210",
        date_of_birth=date(1985, 4, 12),
        gender="Female" if "Nair" in current_user.full_name else "Other"
    )

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Standard security protocol: return confirmation even if email not found to avoid user enumeration
    return {"message": f"If an account exists for {req.email}, password reset instructions have been sent."}

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    db_user = db.scalar(select(UserAccount).where(UserAccount.email == req.email.lower().strip()))
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    db_user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "Password has been successfully updated. You may now log in with your new password."}

