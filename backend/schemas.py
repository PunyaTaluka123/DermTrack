"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List


# ============================================================================
# Authentication Schemas
# ============================================================================
class RegisterIn(BaseModel):
    """Registration request schema"""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """User response schema"""
    id: int
    email: EmailStr
    created_at: str

    class Config:
        from_attributes = True


# ============================================================================
# Patient Schemas
# ============================================================================
class PatientIn(BaseModel):
    """Patient creation/update request schema"""
    name: str
    mrn: Optional[str] = None
    dob: Optional[str] = None
    contact: Optional[str] = None


class PatientOut(BaseModel):
    """Patient response schema"""
    id: int
    name: str
    mrn: Optional[str]
    dob: Optional[str]
    contact: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


# ============================================================================
# Note Schemas
# ============================================================================
class NoteIn(BaseModel):
    """Note creation/update request schema"""
    text: str
    consultation_id: Optional[int] = None


class NoteOut(BaseModel):
    """Note response schema"""
    id: int
    consultation_id: Optional[int]
    text: str
    updated_at: str

    class Config:
        from_attributes = True


# ============================================================================
# Consultation Schemas
# ============================================================================
class ConsultationIn(BaseModel):
    """Consultation creation request schema"""
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    transcript: Optional[str] = None
    audio_filename: Optional[str] = None  # stored filename under media/audio
    audio_url: Optional[str] = None  # absolute URL (e.g., S3)
    consent_given: Optional[bool] = False
    consent_timestamp: Optional[str] = None


class ConsultationOut(BaseModel):
    """Consultation response schema"""
    id: int
    patient_id: Optional[int]
    patient_name: Optional[str]
    transcript: Optional[str]
    audio_url: Optional[str]
    created_at: str
    consent_given: Optional[bool] = None

    class Config:
        from_attributes = True


# ============================================================================
# Consent Schemas
# ============================================================================
class ConsentLogOut(BaseModel):
    """Consent log response schema"""
    id: int
    consultation_id: int
    user_id: int
    patient_id: Optional[int]
    patient_name: Optional[str]
    consent_given: bool
    consent_timestamp: str
    consent_method: str
    ip_address: Optional[str]
    withdrawn: bool

    class Config:
        from_attributes = True


# ============================================================================
# Suggestion Schemas
# ============================================================================
class SuggestIn(BaseModel):
    """Suggestion request schema"""
    text: str
    num: Optional[int] = 5


class SuggestOut(BaseModel):
    """Suggestion response schema"""
    suggestions: List[str]


# ============================================================================
# SOAP Notes Schemas
# ============================================================================
class SoapNotesIn(BaseModel):
    """SOAP notes generation request schema"""
    transcript: str
    notes: str


class SoapNotesOut(BaseModel):
    """SOAP notes response schema"""
    subjective: str
    objective: str
    assessment: str
    plan: str
