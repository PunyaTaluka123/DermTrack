# SQLAlchemy Mapper Initialization Fixes

## Issues Resolved

### 1. Multiple Classes Found Error (Import Time)
**Error:** `Multiple classes found for path "User" in the registry of this declarative base`

**Root Cause:**
- Models in `security_models.py` were using unqualified string references like `relationship("User")`
- SQLAlchemy couldn't determine which `User` class to use when multiple modules cross-import

**Solution:**
Updated all relationship references in `security_models.py` to use fully qualified module paths:
```python
# Before
doctor = relationship("User", foreign_keys=[doctor_id])

# After
doctor = relationship("main.User", foreign_keys=[doctor_id])
```

**Files Changed:**
- `backend/security_models.py` (lines 58, 82, 116, 159)

### 1b. Multiple Classes Found Error (Runtime)
**Error:** `Multiple classes found for path "Note" in the registry of this declarative base` (occurred during HTTP request handling)

**Root Cause:**
- Models within `main.py` were using unqualified string references like `relationship("Note")` and `relationship("User")`
- During uvicorn reload or when handling first HTTP request, SQLAlchemy's mapper configuration fails
- Even though models are in the same file, the reload mechanism causes ambiguity

**Solution:**
Updated all relationship references in `main.py` to use fully qualified module paths:
```python
# Before (User model)
notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")

# After (User model)
notes = relationship("main.Note", back_populates="user", cascade="all, delete-orphan")

# Before (Note model)
user = relationship("User", back_populates="notes")

# After (Note model)
user = relationship("main.User", back_populates="notes")

# Before (Consultation model)
user = relationship("User")

# After (Consultation model)
user = relationship("main.User")
```

**Files Changed:**
- `backend/main.py` (lines 177, 189, 205)

### 2. Table Already Defined Error
**Error:** `Table 'users' is already defined for this MetaData instance`

**Root Cause:**
- Uvicorn's reload mechanism re-imports modules, causing tables to be defined multiple times
- The `extend_existing=True` flag was removed, causing SQLAlchemy to reject duplicate table definitions

**Solution:**
Added `extend_existing=True` back to all model `__table_args__`:
```python
class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    # ... rest of model
```

**Files Changed:**
- `backend/main.py` - Added to User, Note, Consultation, Patient models

### 3. Pydantic V2 Deprecation Warnings
**Warning:** `Support for class-based config is deprecated, use ConfigDict instead`

**Root Cause:**
- Using old Pydantic V1 syntax with `class Config: orm_mode = True`

**Solution:**
Updated all response models to use Pydantic V2 ConfigDict:
```python
# Before
class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: str

    class Config:
        orm_mode = True

# After
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: str
```

**Files Changed:**
- `backend/main.py` - Updated UserOut, NoteOut, ConsultationOut, PatientOut

### 4. FastAPI Startup Event Deprecation
**Warning:** `on_event is deprecated, use lifespan event handlers instead`

**Root Cause:**
- Using deprecated `@app.on_event("startup")` decorator

**Solution:**
Migrated to modern lifespan context manager:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup logic
    init_db()
    print("[OK] All database tables initialized")
    # ... migration logic

    yield

    # Shutdown logic (if needed)
    pass

app = FastAPI(title="DermaTrack API", lifespan=lifespan)
```

**Files Changed:**
- `backend/main.py` - Converted startup event to lifespan context

## Verification

All fixes have been tested and verified:

✅ Application imports without errors
✅ Database initialization creates all 10 tables successfully
✅ SQLAlchemy relationships work correctly between models
✅ Server starts with reload enabled
✅ No deprecation warnings in console output
✅ All CRUD operations with relationships function properly

## Summary of Files Modified

1. **backend/main.py**
   - Added `ConfigDict` import from pydantic
   - Added `asynccontextmanager` import from contextlib
   - Added `extend_existing=True` to all model definitions
   - Updated 4 Pydantic models to use ConfigDict
   - Converted startup event to lifespan context manager

2. **backend/security_models.py**
   - Updated 4 relationship declarations to use `"main.User"` instead of `"User"`

## Testing Commands

```bash
# Test application import
cd backend && python -c "from main import app; print('Success')"

# Test database initialization
cd backend && python -c "from database import init_db; init_db(); print('Success')"

# Test server startup
cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000

# Test with reload
cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Additional Notes

- The bcrypt warning about `__about__` attribute is a known issue with newer bcrypt versions and can be safely ignored
- All security features (RBAC, audit logging, consent management) continue to work correctly
- The application is now fully compatible with the latest versions of FastAPI, Pydantic V2, and SQLAlchemy
