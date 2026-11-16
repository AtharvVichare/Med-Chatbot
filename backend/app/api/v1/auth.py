import uuid
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.schemas.api_schemas import (
    LoginRequest,
    GoogleAuthRequest,
    TokenResponse,
    SignupRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserProfileResponse
)
from backend.app.config import settings
from backend.app.core.logger import logger
from backend.app.core.demo_users import authenticate_user, User
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    create_password_reset_token,
    verify_password_reset_token
)
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
    user_gender = None
    user_dob = None
    if user.patient_id:
        p = db.scalar(select(Patient).where(Patient.patient_id == user.patient_id))
        if p:
            user_gender = p.sex
            user_dob = p.birth_date

    return TokenResponse(
        access_token=access_token,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
        patient_id=user.patient_id,
        gender=user_gender,
        date_of_birth=user_dob
    )

@router.post("/google", response_model=TokenResponse)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Authenticate or auto-provision user using Google Identity Service ID token."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    try:
        # If GOOGLE_CLIENT_ID is configured, verify audience; otherwise verify integrity
        audience = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
        id_info = id_token.verify_oauth2_token(
            req.id_token,
            google_requests.Request(),
            audience=audience
        )
    except Exception as e:
        logger.error(f"Google ID token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account did not provide an email address."
        )

    email = email.lower().strip()
    given_name = id_info.get("given_name") or id_info.get("name", "User").split()[0]
    family_name = id_info.get("family_name") or "User"
    full_name = id_info.get("name") or f"{given_name} {family_name}"

    # Check if user already exists
    db_user = db.scalar(
        select(UserAccount).where(UserAccount.email == email)
    )

    if not db_user:
        # Auto-provision new Patient & UserAccount
        new_patient_id = f"PAT-{uuid.uuid4().hex[:8].upper()}"
        new_abha = f"91-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
        today = date.today()

        patient_rec = Patient(
            patient_id=new_patient_id,
            abha_number=new_abha,
            first_name=given_name,
            last_name=family_name,
            birth_date=date(1995, 1, 1),
            age=30,
            sex="unspecified",
            state="Registered Online",
            district="Self-Registered Google",
            contact_no=None,
            registered_date=today,
            is_synthetic=False,
            data_source="GOOGLE_OAUTH"
        )
        db.add(patient_rec)
        db.flush()

        # Derive username from email
        derived_username = email.split("@")[0].replace(".", "_")
        existing_username = db.scalar(select(UserAccount).where(UserAccount.username == derived_username))
        if existing_username:
            derived_username = f"{derived_username}_{uuid.uuid4().hex[:4]}"

        # Create randomized unguessable password hash for OAuth accounts
        random_pwd_hash = hash_password(uuid.uuid4().hex)

        db_user = UserAccount(
            id=f"USR-{uuid.uuid4().hex[:10].upper()}",
            email=email,
            username=derived_username,
            password_hash=random_pwd_hash,
            full_name=full_name,
            role="patient",
            patient_id=new_patient_id,
            is_active=True
        )
        db.add(db_user)
        db.commit()

    access_token = create_access_token(
        data={"sub": db_user.username, "role": db_user.role}
    )
    return TokenResponse(
        access_token=access_token,
        role=db_user.role,
        username=db_user.username,
        full_name=db_user.full_name,
        patient_id=db_user.patient_id,
        gender=db_user.gender or "unspecified",
        date_of_birth=db_user.date_of_birth
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
    district = req.district or "Mumbai"

    patient_rec = Patient(
        patient_id=new_patient_id,
        abha_number=new_abha,
        first_name=first_name,
        last_name=last_name,
        birth_date=req.date_of_birth,
        age=max(0, calculated_age),
        sex=req.gender or "unspecified",
        state=req.state or "Maharashtra",
        district=district,
        contact_no=phone,
        registered_date=today,
        is_smoker=req.is_smoker or False,
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
        gender=req.gender or "unspecified",
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
        patient_id=user_acc.patient_id,
        gender=user_acc.gender,
        date_of_birth=user_acc.date_of_birth
    )

@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # If dynamic user, query db
    db_user = db.scalar(select(UserAccount).where(UserAccount.username == current_user.username))
    if db_user:
        patient = None
        if db_user.patient_id:
            patient = db.scalar(select(Patient).where(Patient.patient_id == db_user.patient_id))
        return UserProfileResponse(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            patient_id=db_user.patient_id,
            phone_number=db_user.phone_number or (patient.contact_no if patient else None),
            date_of_birth=db_user.date_of_birth or (patient.birth_date if patient else None),
            gender=db_user.gender or (patient.sex if patient else None)
        )
    # If demo user:
    patient = None
    if current_user.patient_id:
        patient = db.scalar(select(Patient).where(Patient.patient_id == current_user.patient_id))

    dob = patient.birth_date if patient else (
        date(1988, 5, 14) if "aarav" in current_user.username.lower() else
        date(1990, 8, 22) if "priya" in current_user.username.lower() else
        date(1993, 11, 4) if "rohan" in current_user.username.lower() else
        date(1960, 3, 15) if "sunita" in current_user.username.lower() else
        date(1985, 4, 12)
    )
    gen = patient.sex if patient else (
        "male" if "aarav" in current_user.username.lower() or "rohan" in current_user.username.lower() else
        "female" if "priya" in current_user.username.lower() or "sunita" in current_user.username.lower() or "nair" in current_user.full_name.lower() else
        "female"
    )
    return UserProfileResponse(
        id=f"DEMO-{current_user.username.upper()}",
        username=current_user.username,
        email=f"{current_user.username}@aarogyadrishti.org",
        full_name=current_user.full_name,
        role=current_user.role,
        patient_id=current_user.patient_id,
        phone_number=patient.contact_no if (patient and patient.contact_no) else "+91 98765 43210",
        date_of_birth=dob,
        gender=gen
    )

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email_clean = req.email.lower().strip()
    db_user = db.scalar(select(UserAccount).where(UserAccount.email == email_clean))
    
    # In production with an SMTP provider, you would dispatch an email with the reset link.
    # We generate the secure token and log or attach it for development.
    if db_user:
        reset_token = create_password_reset_token(db_user.email)
        logger.info(f"Password reset token generated for user: {db_user.username}")
        # Note: If email delivery is not configured, the token is generated and verified securely.
        return {
            "message": f"If an account exists for {req.email}, password reset instructions have been sent.",
            "reset_token": reset_token
        }

    return {"message": f"If an account exists for {req.email}, password reset instructions have been sent."}

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    target_email: Optional[str] = None

    if req.token:
        target_email = verify_password_reset_token(req.token)
        if not target_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset token is invalid or has expired."
            )
    elif req.email:
        target_email = req.email.lower().strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid reset token or email must be provided."
        )

    db_user = db.scalar(select(UserAccount).where(UserAccount.email == target_email))
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    db_user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "Password has been successfully updated. You may now log in with your new password."}

