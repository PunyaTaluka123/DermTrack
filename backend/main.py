from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uvicorn
import os
from datetime import datetime, timedelta

# Database and auth imports
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, create_engine, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import secrets

# ----------------------------------------------------
# Config
# ----------------------------------------------------
TRANSCRIBE_BACKEND = os.getenv("TRANSCRIBE_BACKEND", "local").lower()
RAW_FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
FRONTEND_ORIGINS = [origin.strip() for origin in RAW_FRONTEND_ORIGINS.split(",") if origin.strip()]
if not FRONTEND_ORIGINS:
    FRONTEND_ORIGINS = ["http://localhost:3000"]
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").lower() in ("1", "true", "yes")
SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN") or None
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax").lower()
if SESSION_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    SESSION_COOKIE_SAMESITE = "lax"

# Optional S3 audio storage
S3_ENABLED = os.getenv("S3_ENABLED", "false").lower() in ("1", "true", "yes")
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_REGION = os.getenv("AWS_REGION", os.getenv("S3_REGION", ""))
S3_PREFIX = os.getenv("S3_PREFIX", "dermatrack/audio/")
S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL", "")

app = FastAPI(title="DermaTrack API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Path("media/audio").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

# ----------------------------------------------------
# Database setup
# ----------------------------------------------------
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    mrn = Column(String(255), nullable=True)
    dob = Column(String(32), nullable=True)
    contact = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_patient_user_name'),)


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


class ConsultationOut(BaseModel):
    id: int
    patient_id: Optional[int]
    patient_name: Optional[str]
    transcript: Optional[str]
    audio_url: Optional[str]
    created_at: str

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


# ----------------------------------------------------
# Routes
# ----------------------------------------------------
@app.on_event("startup")
def _startup():
    init_db()
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
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
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
def login(form: RegisterIn, response: Response, db: Session = Depends(get_db)):
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
    name = (payload.name or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    existing = db.query(Patient).filter(Patient.user_id == user.id, Patient.name == name).first()
    if existing:
        return PatientOut(id=existing.id, name=existing.name, mrn=existing.mrn, dob=existing.dob, contact=existing.contact, created_at=existing.created_at.isoformat() + "Z")
    p = Patient(user_id=user.id, name=name, mrn=payload.mrn, dob=payload.dob, contact=payload.contact)
    db.add(p)
    db.commit()
    db.refresh(p)
    return PatientOut(id=p.id, name=p.name, mrn=p.mrn, dob=p.dob, contact=p.contact, created_at=p.created_at.isoformat() + "Z")


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


@app.get("/notes", response_model=List[NoteOut])
def list_notes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Note).filter(Note.user_id == user.id).order_by(Note.updated_at.desc()).all()
    return [NoteOut(id=n.id, consultation_id=_as_int_or_none(n.consultation_id), text=n.text, updated_at=n.updated_at.isoformat() + "Z") for n in items]


@app.post("/notes", response_model=NoteOut)
def create_note(note: NoteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = Note(user_id=user.id, consultation_id=note.consultation_id, text=note.text)
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
    n.text = payload.text
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
def create_consultation(payload: ConsultationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resolved_audio_url = payload.audio_url or None
    audio_path_str = None
    # Resolve patient
    pid = payload.patient_id
    if not pid and payload.patient_name:
        name = payload.patient_name.strip()
        if name:
            existing = db.query(Patient).filter(Patient.user_id == user.id, Patient.name == name).first()
            if existing:
                pid = existing.id
            else:
                p = Patient(user_id=user.id, name=name)
                db.add(p)
                db.flush()
                pid = p.id
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
    )


@app.get("/consultations", response_model=List[ConsultationOut])
def list_consultations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Consultation).filter(Consultation.user_id == user.id).order_by(Consultation.created_at.desc()).all()
    out: List[ConsultationOut] = []
    for c in items:
        audio_url = c.audio_url or (f"/media/audio/{Path(c.audio_path).name}" if c.audio_path else None)
        pname = None
        if c.patient_id:
            p = db.query(Patient).filter(Patient.id == c.patient_id, Patient.user_id == user.id).first()
            pname = p.name if p else None
        out.append(ConsultationOut(
            id=c.id,
            patient_id=c.patient_id,
            patient_name=pname,
            transcript=c.transcript,
            audio_url=audio_url,
            created_at=c.created_at.isoformat() + "Z",
        ))
    return out


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    try:
        content = await audio.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file")
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
            from faster_whisper import WhisperModel
            model_size = os.getenv("WHISPER_MODEL_SIZE", os.getenv("WHISPER_MODEL", "small"))
            model = WhisperModel(model_size)
            segments, _ = model.transcribe(str(audio_file_path))
            text = " ".join([segment["text"] for segment in segments])
        return {"text": text or "", "audio_filename": fn, "audio_url": audio_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
