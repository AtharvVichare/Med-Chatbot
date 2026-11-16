from datetime import date
from typing import Optional, Any, List, Dict
from pydantic import BaseModel, ConfigDict

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str
    patient_id: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class GoogleAuthRequest(BaseModel):
    id_token: str

class SignupRequest(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    username: str
    password: str
    date_of_birth: date
    gender: Optional[str] = "unspecified"
    phone_number: Optional[str] = None
    phone: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = "Maharashtra"
    is_smoker: Optional[bool] = False
    blood_group: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: Optional[str] = None
    email: Optional[str] = None
    new_password: str

class UserProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    patient_id: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None

class TimelineEvent(BaseModel):
    event_id: str
    event_type: str  # 'encounter', 'condition', 'observation', 'medication'
    patient_id: str
    encounter_id: Optional[str] = None
    event_date: date
    clinical_details: Dict[str, Any]
    source_table: str

class TimelineResponse(BaseModel):
    patient_id: str
    total_events: int
    events: List[TimelineEvent]

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[Any]

class ObservationTrendPoint(BaseModel):
    date: str
    value: float
    unit: str
    source_type: str  # 'lab_observation' or 'home_daily_log'
    reference_range: Optional[str] = None
    interpretation: Optional[str] = None
    test_name: str

class LongitudinalGraphResponse(BaseModel):
    patient_id: str
    test_category: str
    metric_name: str
    unit: str
    points_count: int
    data: List[ObservationTrendPoint]
    latest_value: Optional[float] = None
    previous_value: Optional[float] = None
    change_value: Optional[float] = None
    change_direction: Optional[str] = None  # 'increased', 'decreased', 'stable'
    latest_date: Optional[str] = None
    disclaimer: str


