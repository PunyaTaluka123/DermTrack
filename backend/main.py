from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uvicorn
import os
from datetime import datetime, timedelta
from google import genai
import json
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import bleach

# Database and auth imports
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, create_engine, UniqueConstraint, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session, joinedload
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import secrets

from config import *
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="DermaTrack API")

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Restrict to specific methods
    allow_headers=["Content-Type", "Authorization", "Cookie"],  # Restrict headers
)
Path("media/audio").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

# ----------------------------------------------------
# Database setup
# ----------------------------------------------------
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Configure connection pooling for better performance and reliability
if DB_URL.startswith("sqlite"):
    engine = create_engine(
        DB_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True  # Verify connections before using them
    )
else:
    engine = create_engine(
        DB_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),  # Default 10 connections
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),  # Allow up to 20 additional connections
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes")
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)
    text = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    user = relationship("User", back_populates="notes")


class Consultation(Base):
    __tablename__ = "consultations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor = Column(String(255), nullable=True)  # legacy
    patient = Column(String(255), nullable=True) # legacy free text
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True, index=True)
    audio_path = Column(String(1024), nullable=True)
    audio_url = Column(String(2048), nullable=True)
    transcript = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    user = relationship("User")
    patient_rel = relationship("Patient")


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    mrn = Column(String(255), nullable=True)
    dob = Column(String(32), nullable=True)
    contact = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_patient_user_name'),)


class ConsultationConsent(Base):
    """Records consent confirmation for specific consultation recording/transcription"""
    __tablename__ = "consultation_consents"

    id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True, index=True)

    # Consent details
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime, nullable=False, index=True)
    consent_method = Column(String(100), default="verbal", nullable=False)

    # Audit information
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    # Optional withdrawal tracking
    withdrawn = Column(Boolean, default=False, nullable=False, index=True)
    withdrawn_at = Column(DateTime, nullable=True)

    # Additional notes
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User")
    consultation = relationship("Consultation", backref="consent")
    patient = relationship("Patient")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _as_int_or_none(value) -> Optional[int]:
    try:
        if value is None:
            return None
        s = str(value).strip()
        if s == "":
            return None
        return int(s)
    except Exception:
        return None


# ----------------------------------------------------
# Auth utils
# ----------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def validate_password_strength(password: str) -> None:
    """Validate password meets security requirements"""
    if len(password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters long")
    if not any(c.isupper() for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")


def sanitize_html(text: str) -> str:
    """Sanitize user input to prevent XSS attacks"""
    if not text:
        return text
    # Allow basic formatting but strip dangerous tags
    allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li']
    return bleach.clean(text, tags=allowed_tags, strip=True)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ----------------------------------------------------
# Schemas
# ----------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: str

    class Config:
        orm_mode = True


class NoteIn(BaseModel):
    text: str
    consultation_id: Optional[int] = None


class NoteOut(BaseModel):
    id: int
    consultation_id: Optional[int]
    text: str
    updated_at: str

    class Config:
        orm_mode = True


# Suggestion Schemas
class SuggestIn(BaseModel):
    text: str
    num: Optional[int] = 5


class SuggestOut(BaseModel):
    suggestions: List[str]


# Consultation Schemas
class ConsultationIn(BaseModel):
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    transcript: Optional[str] = None
    audio_filename: Optional[str] = None  # stored filename under media/audio
    audio_url: Optional[str] = None       # absolute URL (e.g., S3)
    consent_given: Optional[bool] = False
    consent_timestamp: Optional[str] = None


class ConsultationOut(BaseModel):
    id: int
    patient_id: Optional[int]
    patient_name: Optional[str]
    transcript: Optional[str]
    audio_url: Optional[str]
    created_at: str
    consent_given: Optional[bool] = None

    class Config:
        orm_mode = True


class ConsentLogOut(BaseModel):
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
        orm_mode = True


class PatientIn(BaseModel):
    name: str
    mrn: Optional[str] = None
    dob: Optional[str] = None
    contact: Optional[str] = None


class PatientOut(BaseModel):
    id: int
    name: str
    mrn: Optional[str]
    dob: Optional[str]
    contact: Optional[str]
    created_at: str

    class Config:
        orm_mode = True


# SOAP Notes Schemas
class SoapNotesIn(BaseModel):
    transcript: str
    notes: str


class SoapNotesOut(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str


# ----------------------------------------------------
# Routes
# ----------------------------------------------------
@app.on_event("startup")
def _startup():
    global whisper_model
    validate_config()
    init_db()

    # Load Whisper model once at startup if using local transcription
    if TRANSCRIBE_BACKEND == "local":
        try:
            from faster_whisper import WhisperModel
            model_size = os.getenv("WHISPER_MODEL_SIZE", os.getenv("WHISPER_MODEL", "small"))
            print(f"Loading Whisper model ({model_size})...")
            whisper_model = WhisperModel(model_size)
            print("Whisper model loaded successfully")
        except Exception as e:
            print(f"WARNING: Failed to load Whisper model: {e}")
            print("Transcription will not be available")

    # Lightweight migration: backfill patients from legacy consultation.patient
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            users = db.query(User).all()
            for u in users:
                legacy = db.query(Consultation).filter(
                    Consultation.user_id == u.id,
                    Consultation.patient_id == None,
                    Consultation.patient != None
                ).all()
                if not legacy:
                    continue
                # map patient name -> id per user
                name_to_id = {}
                for c in legacy:
                    pname = (c.patient or '').strip()
                    if not pname:
                        continue
                    pid = name_to_id.get(pname)
                    if not pid:
                        p = db.query(Patient).filter(Patient.user_id == u.id, Patient.name == pname).first()
                        if not p:
                            p = Patient(user_id=u.id, name=pname)
                            db.add(p)
                            db.flush()
                        pid = p.id
                        name_to_id[pname] = pid
                    c.patient_id = pid
                db.commit()
        finally:
            db.close()
    except Exception:
        # best-effort migration only
        pass


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/auth/register", response_model=UserOut)
@limiter.limit("5/hour")
def register(request: Request, payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    validate_password_strength(payload.password)
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=SECURE_COOKIES,
        domain=SESSION_COOKIE_DOMAIN,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return UserOut(id=user.id, email=user.email, created_at=user.created_at.isoformat() + "Z")


@app.post("/auth/login", response_model=UserOut)
@limiter.limit("10/minute")
def login(request: Request, form: RegisterIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.email.lower()).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=SECURE_COOKIES,
        domain=SESSION_COOKIE_DOMAIN,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return UserOut(id=user.id, email=user.email, created_at=user.created_at.isoformat() + "Z")


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token", domain=SESSION_COOKIE_DOMAIN)
    return {"ok": True}


@app.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, created_at=user.created_at.isoformat() + "Z")


@app.get("/patients", response_model=List[PatientOut])
def list_patients(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Patient).filter(Patient.user_id == user.id).order_by(Patient.created_at.desc()).all()
    return [PatientOut(id=p.id, name=p.name, mrn=p.mrn, dob=p.dob, contact=p.contact, created_at=p.created_at.isoformat() + "Z") for p in items]


@app.post("/patients", response_model=PatientOut)
def create_patient(payload: PatientIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    name = sanitize_html((payload.name or '').strip())
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    existing = db.query(Patient).filter(Patient.user_id == user.id, Patient.name == name).first()
    if existing:
        return PatientOut(id=existing.id, name=existing.name, mrn=existing.mrn, dob=existing.dob, contact=existing.contact, created_at=existing.created_at.isoformat() + "Z")
    sanitized_contact = sanitize_html(payload.contact) if payload.contact else None
    p = Patient(user_id=user.id, name=name, mrn=payload.mrn, dob=payload.dob, contact=sanitized_contact)
    db.add(p)
    try:
        db.commit()
        db.refresh(p)
        return PatientOut(id=p.id, name=p.name, mrn=p.mrn, dob=p.dob, contact=p.contact, created_at=p.created_at.isoformat() + "Z")
    except IntegrityError:
        # Race condition: another request created the same patient
        db.rollback()
        existing = db.query(Patient).filter(Patient.user_id == user.id, Patient.name == name).first()
        if existing:
            return PatientOut(id=existing.id, name=existing.name, mrn=existing.mrn, dob=existing.dob, contact=existing.contact, created_at=existing.created_at.isoformat() + "Z")
        raise HTTPException(status_code=500, detail="Failed to create patient")


@app.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.id == patient_id, Patient.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientOut(id=p.id, name=p.name, mrn=p.mrn, dob=p.dob, contact=p.contact, created_at=p.created_at.isoformat() + "Z")


@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.id == patient_id, Patient.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    # Collect consultation ids
    cids = [cid for (cid,) in db.query(Consultation.id).filter(Consultation.user_id == user.id, Consultation.patient_id == patient_id).all()]
    if cids:
        # Delete notes under these consultations
        db.query(Note).filter(Note.user_id == user.id, Note.consultation_id.in_(cids)).delete(synchronize_session=False)
        # Delete consultations
        db.query(Consultation).filter(Consultation.user_id == user.id, Consultation.patient_id == patient_id).delete(synchronize_session=False)
    # Delete patient
    db.delete(p)
    db.commit()
    return {"ok": True}


@app.get("/patients/{patient_id}/consultations", response_model=List[ConsultationOut])
def list_patient_consultations(patient_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # verify ownership
    p = db.query(Patient).filter(Patient.id == patient_id, Patient.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    items = db.query(Consultation).filter(Consultation.user_id == user.id, Consultation.patient_id == patient_id).order_by(Consultation.created_at.desc()).all()
    out: List[ConsultationOut] = []
    for c in items:
        audio_url = c.audio_url or (f"/media/audio/{Path(c.audio_path).name}" if c.audio_path else None)
        out.append(ConsultationOut(
            id=c.id,
            patient_id=c.patient_id,
            patient_name=p.name,
            transcript=c.transcript,
            audio_url=audio_url,
            created_at=c.created_at.isoformat() + "Z",
        ))
    return out


@app.get("/patients/{patient_id}/notes", response_model=List[NoteOut])
def list_patient_notes(patient_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # verify ownership
    p = db.query(Patient).filter(Patient.id == patient_id, Patient.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    cids = [c.id for c in db.query(Consultation.id).filter(Consultation.user_id == user.id, Consultation.patient_id == patient_id).all()]
    if not cids:
        return []
    items = db.query(Note).filter(Note.user_id == user.id, Note.consultation_id.in_(cids)).order_by(Note.updated_at.desc()).all()
    return [NoteOut(id=n.id, consultation_id=_as_int_or_none(n.consultation_id), text=n.text, updated_at=n.updated_at.isoformat() + "Z") for n in items]


def _suggest_questions_from_text(text: str, n: int = 5) -> List[str]:
    t = (text or "").lower()
    base: List[str] = []
    # General dermatology prompts
    base.extend([
        "When did these symptoms first start, and have they changed over time?",
        "On a scale of 1–10, how severe are the symptoms right now?",
        "Have you noticed any triggers (e.g., new products, heat, stress, foods)?",
        "What treatments or home remedies have you tried, and did they help?",
        "Do you have any photos showing how it looked at its worst?",
    ])
    if any(k in t for k in ["itch", "itchy", "pruritus"]):
        base.append("Is the area itchy throughout the day or worse at night?")
        base.append("Does antihistamine or cold compress reduce the itch?")
    if any(k in t for k in ["pain", "tender", "sore"]):
        base.append("Is the area painful to touch or only with movement?")
        base.append("Have you noticed swelling, warmth, or fever with the pain?")
    if any(k in t for k in ["rash", "red", "patch", "lesion", "spots"]):
        base.append("Where on the body did the rash start, and did it spread?")
        base.append("Do the lesions blanch (turn white) when pressed?")
    if any(k in t for k in ["acne", "pimple", "blackhead", "whitehead"]):
        base.append("Do breakouts correlate with menstrual cycle, stress, or diet?")
        base.append("What is your current skincare routine (cleanser, actives, SPF)?")
    if any(k in t for k in ["eczema", "dermatitis", "atopic"]):
        base.append("Any family history of eczema, asthma, or allergies?")
        base.append("How often do you moisturize and what products do you use?")
    if any(k in t for k in ["psoriasis", "plaque", "silvery scale"]):
        base.append("Any joint pain or stiffness suggestive of psoriatic arthritis?")
        base.append("Have you tried topical steroids or vitamin D analogues?")
    if any(k in t for k in ["infection", "pus", "ooze", "crust"]):
        base.append("Have you had recent antibiotic use or noticed spreading redness?")
    if any(k in t for k in ["allergy", "allergic", "contact"]):
        base.append("Any new detergents, fragrances, jewelry, or cosmetics recently?")
    # De-duplicate and return top n
    seen = set()
    dedup = []
    for q in base:
        if q not in seen:
            seen.add(q)
            dedup.append(q)
    return dedup[: max(3, min(5, n or 5))]


@app.post("/suggest_questions", response_model=SuggestOut)
def suggest_questions(payload: SuggestIn) -> SuggestOut:
    try:
        suggestions = _suggest_questions_from_text(payload.text, payload.num or 5)
        # Ensure 3–5 bounds
        if len(suggestions) < 3:
            suggestions.extend([
                "Have you changed soaps, shampoos, or detergents recently?",
                "Is there a family history of similar skin issues?",
                "Do symptoms improve indoors or worsen after sun exposure?",
            ])
            suggestions = suggestions[:5]
        return SuggestOut(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestion error: {str(e)}")


@app.post("/soap_autofill", response_model=SoapNotesOut)
def soap_autofill(payload: SoapNotesIn, user: User = Depends(get_current_user)) -> SoapNotesOut:
    """
    Generate SOAP notes from transcript and live notes using Gemini API.
    """
    # Combine transcript and notes for context
    combined_input = ""
    if payload.transcript.strip():
        combined_input += f"TRANSCRIPT:\n{payload.transcript.strip()}\n\n"
    if payload.notes.strip():
        combined_input += f"CLINICIAN NOTES:\n{payload.notes.strip()}\n\n"

    if not combined_input.strip():
        raise HTTPException(status_code=400, detail="Both transcript and notes are empty")
    print("Combined Input for Gemini:", combined_input)
    # Create the prompt for Gemini
    prompt = f"""You are a medical documentation assistant helping to organize consultation notes into SOAP format (Subjective, Objective, Assessment, Plan).

Below is the information from a dermatology consultation:
{combined_input}

Please extract and organize this information into the following four SOAP sections. Be concise and professional. If a section has no relevant information, write "No information provided" for that section.

Return your response as a JSON object with these exact keys: "subjective", "objective", "assessment", "plan"

SOAP Section Guidelines:
- Subjective: Patient's chief complaint, symptoms, history as described by the patient (what they say)
- Objective: Observable findings, clinical observations, measurements, examination results (what you see/measure)
- Assessment: Clinical diagnosis, impression, or differential diagnoses
- Plan: Treatment plan, medications, follow-up instructions, recommendations

Respond ONLY with valid JSON in this exact format:
{{
  "subjective": "content here",
  "objective": "content here",
  "assessment": "content here",
  "plan": "content here"
}}"""

    try:
        # Initialize Gemini model
        if not GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
        model="gemini-2.5-flash",
    contents=prompt
)

        # Extract the text from response
        response_text = response.text.strip()
        print("Gemini Response Text:", response_text)
        # Try to extract JSON from the response
        # Sometimes Gemini wraps JSON in markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON response
        try:
            soap_data = json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract sections manually
            raise HTTPException(status_code=500, detail="Failed to parse Gemini response as JSON")

        # Validate that all required keys are present
        required_keys = ["subjective", "objective", "assessment", "plan"]
        for key in required_keys:
            if key not in soap_data:
                soap_data[key] = "No information provided"

        return SoapNotesOut(
            subjective=soap_data.get("subjective", "No information provided"),
            objective=soap_data.get("objective", "No information provided"),
            assessment=soap_data.get("assessment", "No information provided"),
            plan=soap_data.get("plan", "No information provided")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating SOAP notes: {str(e)}")


@app.get("/notes", response_model=List[NoteOut])
def list_notes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Note).filter(Note.user_id == user.id).order_by(Note.updated_at.desc()).all()
    return [NoteOut(id=n.id, consultation_id=_as_int_or_none(n.consultation_id), text=n.text, updated_at=n.updated_at.isoformat() + "Z") for n in items]


@app.post("/notes", response_model=NoteOut)
def create_note(note: NoteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sanitized_text = sanitize_html(note.text)
    n = Note(user_id=user.id, consultation_id=note.consultation_id, text=sanitized_text)
    db.add(n)
    db.commit()
    db.refresh(n)
    return NoteOut(id=n.id, consultation_id=_as_int_or_none(n.consultation_id), text=n.text, updated_at=n.updated_at.isoformat() + "Z")


@app.get("/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteOut(id=n.id, consultation_id=_as_int_or_none(n.consultation_id), text=n.text, updated_at=n.updated_at.isoformat() + "Z")


@app.put("/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: int, payload: NoteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Note not found")
    n.text = sanitize_html(payload.text)
    n.consultation_id = payload.consultation_id
    n.updated_at = datetime.utcnow()
    db.add(n)
    db.commit()
    db.refresh(n)
    return NoteOut(id=n.id, consultation_id=_as_int_or_none(n.consultation_id), text=n.text, updated_at=n.updated_at.isoformat() + "Z")


@app.delete("/notes/{note_id}")
def delete_note(note_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(n)
    db.commit()
    return {"ok": True}


@app.post("/consultations", response_model=ConsultationOut)
def create_consultation(payload: ConsultationIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    resolved_audio_url = payload.audio_url or None
    audio_path_str = None
    # Resolve patient
    pid = payload.patient_id
    if not pid and payload.patient_name:
        name = sanitize_html(payload.patient_name.strip())
        if name:
            existing = db.query(Patient).filter(Patient.user_id == user.id, Patient.name == name).first()
            if existing:
                pid = existing.id
            else:
                p = Patient(user_id=user.id, name=name)
                db.add(p)
                try:
                    db.flush()
                    pid = p.id
                except IntegrityError:
                    # Race condition: another request created the same patient
                    db.rollback()
                    existing = db.query(Patient).filter(Patient.user_id == user.id, Patient.name == name).first()
                    if existing:
                        pid = existing.id
                    else:
                        raise HTTPException(status_code=500, detail="Failed to create patient")
    if payload.audio_filename:
        # Validate file exists under media/audio
        audio_path = Path("media") / "audio" / payload.audio_filename
        if audio_path.exists():
            audio_path_str = str(audio_path)
            if not resolved_audio_url:
                resolved_audio_url = f"/media/audio/{payload.audio_filename}"
    c = Consultation(
        user_id=user.id,
        patient_id=pid,
        transcript=payload.transcript or "",
        audio_path=audio_path_str,
        audio_url=resolved_audio_url,
    )
    db.add(c)
    db.flush()  # Get consultation ID before creating consent record

    # Create consent record if consent data provided
    if payload.consent_given and payload.consent_timestamp:
        consent_ts = datetime.fromisoformat(payload.consent_timestamp.replace('Z', '+00:00'))
        consent = ConsultationConsent(
            consultation_id=c.id,
            user_id=user.id,
            patient_id=pid,
            consent_given=payload.consent_given,
            consent_timestamp=consent_ts,
            consent_method="verbal",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
        db.add(consent)
        db.flush()  # Get consent ID for audit log

        # Log consent action to audit trail
        try:
            from security.audit import AuditLogger
            patient_ref = f"patient_{pid}" if pid else "unknown"
            AuditLogger.log_consent_action(
                db=db,
                user_id=user.id,
                patient_ref=patient_ref,
                action="consent_granted",
                consent_id=str(consent.id),
                request=request
            )
        except Exception as e:
            # Don't fail the consultation creation if audit logging fails
            print(f"Warning: Failed to log consent action: {e}")

    db.commit()
    db.refresh(c)
    pname = None
    if c.patient_id:
        p = db.query(Patient).filter(Patient.id == c.patient_id, Patient.user_id == user.id).first()
        pname = p.name if p else None
    return ConsultationOut(
        id=c.id,
        patient_id=c.patient_id,
        patient_name=pname,
        transcript=c.transcript,
        audio_url=c.audio_url or (f"/media/audio/{Path(c.audio_path).name}" if c.audio_path else None),
        created_at=c.created_at.isoformat() + "Z",
        consent_given=payload.consent_given,
    )


@app.get("/consultations", response_model=List[ConsultationOut])
def list_consultations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Use joinedload to prevent N+1 query problem
    items = db.query(Consultation)\
        .options(joinedload(Consultation.patient_rel))\
        .filter(Consultation.user_id == user.id)\
        .order_by(Consultation.created_at.desc())\
        .all()
    out: List[ConsultationOut] = []
    for c in items:
        audio_url = c.audio_url or (f"/media/audio/{Path(c.audio_path).name}" if c.audio_path else None)
        pname = None
        if c.patient_rel:
            pname = c.patient_rel.name

        # Check if consent exists for this consultation
        consent = db.query(ConsultationConsent).filter(ConsultationConsent.consultation_id == c.id).first()
        consent_given = consent.consent_given if consent else None

        out.append(ConsultationOut(
            id=c.id,
            patient_id=c.patient_id,
            patient_name=pname,
            transcript=c.transcript,
            audio_url=audio_url,
            created_at=c.created_at.isoformat() + "Z",
            consent_given=consent_given,
        ))
    return out


# ============================================================================
# Consent Logging Endpoints
# ============================================================================

@app.get("/consent-logs", response_model=List[ConsentLogOut])
def get_my_consent_logs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all consent logs for the current user (doctor's own consultations)"""
    consents = db.query(ConsultationConsent)\
        .filter(ConsultationConsent.user_id == user.id)\
        .order_by(ConsultationConsent.consent_timestamp.desc())\
        .all()

    out: List[ConsentLogOut] = []
    for consent in consents:
        pname = None
        if consent.patient_id:
            patient = db.query(Patient).filter(Patient.id == consent.patient_id).first()
            pname = patient.name if patient else None

        out.append(ConsentLogOut(
            id=consent.id,
            consultation_id=consent.consultation_id,
            user_id=consent.user_id,
            patient_id=consent.patient_id,
            patient_name=pname,
            consent_given=consent.consent_given,
            consent_timestamp=consent.consent_timestamp.isoformat() + "Z",
            consent_method=consent.consent_method,
            ip_address=consent.ip_address,
            withdrawn=consent.withdrawn,
        ))
    return out


@app.get("/admin/consent-logs", response_model=List[ConsentLogOut])
def get_all_consent_logs(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin endpoint: Get all consent logs across all users"""
    # Note: In production, add RBAC check here to ensure user has admin role
    # For now, any authenticated user can access this (you may want to restrict)

    # Log admin access to consent logs
    try:
        from security.audit import AuditLogger
        AuditLogger.log(
            db=db,
            action="read",
            resource_type="consent_logs",
            user_id=user.id,
            resource_id="all",
            request=request,
            success=True,
            metadata={"admin_access": True}
        )
    except Exception as e:
        print(f"Warning: Failed to log admin consent access: {e}")

    consents = db.query(ConsultationConsent)\
        .order_by(ConsultationConsent.consent_timestamp.desc())\
        .all()

    out: List[ConsentLogOut] = []
    for consent in consents:
        pname = None
        if consent.patient_id:
            patient = db.query(Patient).filter(Patient.id == consent.patient_id).first()
            pname = patient.name if patient else None

        out.append(ConsentLogOut(
            id=consent.id,
            consultation_id=consent.consultation_id,
            user_id=consent.user_id,
            patient_id=consent.patient_id,
            patient_name=pname,
            consent_given=consent.consent_given,
            consent_timestamp=consent.consent_timestamp.isoformat() + "Z",
            consent_method=consent.consent_method,
            ip_address=consent.ip_address,
            withdrawn=consent.withdrawn,
        ))
    return out


@app.get("/consultations/{consultation_id}/consent", response_model=ConsentLogOut)
def get_consultation_consent(consultation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get consent record for a specific consultation"""
    # Verify the consultation belongs to the user
    consultation = db.query(Consultation).filter(
        Consultation.id == consultation_id,
        Consultation.user_id == user.id
    ).first()
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    consent = db.query(ConsultationConsent).filter(
        ConsultationConsent.consultation_id == consultation_id
    ).first()

    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found")

    pname = None
    if consent.patient_id:
        patient = db.query(Patient).filter(Patient.id == consent.patient_id).first()
        pname = patient.name if patient else None

    return ConsentLogOut(
        id=consent.id,
        consultation_id=consent.consultation_id,
        user_id=consent.user_id,
        patient_id=consent.patient_id,
        patient_name=pname,
        consent_given=consent.consent_given,
        consent_timestamp=consent.consent_timestamp.isoformat() + "Z",
        consent_method=consent.consent_method,
        ip_address=consent.ip_address,
        withdrawn=consent.withdrawn,
    )


@app.post("/transcribe")
@limiter.limit("20/hour")
async def transcribe(request: Request, audio: UploadFile = File(...)):
    try:
        # Validate file size (max 50MB)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes
        content = await audio.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file")
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB")

        # Validate content type
        if audio.content_type and not audio.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="Invalid file type. Only audio files are allowed")

        # Validate file extension
        filename = audio.filename or ""
        allowed_extensions = [".webm", ".wav", ".mp3", ".m4a", ".ogg", ".flac"]
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            raise HTTPException(status_code=400, detail=f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}")
        # Persist audio to disk under media/audio
        fn = f"consult_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{secrets.token_hex(6)}.webm"
        audio_file_path = Path("media") / "audio" / fn
        with open(audio_file_path, "wb") as f:
            f.write(content)
        audio_url = f"/media/audio/{fn}"

        # Optional S3 upload
        if S3_ENABLED and S3_BUCKET:
            try:
                import boto3  # type: ignore
                s3 = boto3.client("s3", region_name=S3_REGION or None)
                key = (S3_PREFIX or "").rstrip("/") + "/" + fn if S3_PREFIX else fn
                s3.upload_file(str(audio_file_path), S3_BUCKET, key, ExtraArgs={"ContentType": "audio/webm"})
                if S3_PUBLIC_URL:
                    audio_url = (S3_PUBLIC_URL.rstrip("/") + "/" + key).replace("//", "/").replace(":/", "://")
                elif S3_REGION:
                    audio_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"
                else:
                    audio_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"
            except Exception:
                audio_url = f"/media/audio/{fn}"
        if TRANSCRIBE_BACKEND == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            with open(audio_file_path, "rb") as f:
                resp = client.audio.transcriptions.create(
                    file=f,
                    model="whisper-1",
                    response_format="text"
                )
            text = resp.text if hasattr(resp, 'text') else resp.get("text", "")
        else:
            # Use pre-loaded Whisper model
            if whisper_model is None:
                raise HTTPException(status_code=503, detail="Whisper model not loaded. Please check server configuration.")
            segments, _ = whisper_model.transcribe(str(audio_file_path))
            # Fix: segments is an iterator, not a list of dicts
            text = " ".join([seg.text for seg in segments])
        return {"text": text or "", "audio_filename": fn, "audio_url": audio_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
