# Security Integration Guide

This guide shows how to integrate the security infrastructure into your DermTrack application.

## Quick Start

### 1. Initialize Database Schema

```python
# Add to main.py startup
from security_models import Base

@app.on_event("startup")
def _startup():
    # Existing initialization
    init_db()

    # Add security tables
    Base.metadata.create_all(bind=engine)
    print("Security tables created")
```

### 2. Import Security Modules

Add to top of `main.py`:

```python
from security.encryption import EncryptionManager
from security.rbac import RBACManager, require_permission, require_role
from security.audit import AuditLogger, audit_action
from data_lifecycle import LifecycleManager
from security_models import ConsentRecord, AuditLog, DataLifecycleRecord, UserRole, UserRoleAssignment
```

### 3. Protect Routes with RBAC

Example: Protect patient data access

```python
from fastapi import Request

@app.get("/patients/{patient_id}")
def get_patient(
    patient_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = Request
):
    # Check permission
    if not RBACManager.has_permission(user.id, "read_patient_data", db):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Log access
    AuditLogger.log_data_access(
        db=db,
        user_id=user.id,
        resource_type="patient",
        resource_id=str(patient_id),
        action="read",
        request=request
    )

    # Existing logic
    p = db.query(Patient).filter(Patient.id == patient_id, Patient.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")

    return PatientOut(...)
```

### 4. Add Lifecycle Tracking to File Uploads

Update the `/transcribe` endpoint:

```python
@app.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = Request
):
    # Save file
    content = await audio.read()
    fn = f"consult_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{secrets.token_hex(6)}.webm"
    audio_file_path = Path("data_storage/raw_data") / fn  # Changed to segregated storage

    with open(audio_file_path, "wb") as f:
        f.write(content)

    # Register in lifecycle system
    manager = LifecycleManager(db)
    lifecycle_metadata = manager.register_file(
        file_path=audio_file_path,
        file_type="raw_audio",  # Triggers 24h retention
        user_id=user.id,
        consultation_id=None,  # Will be set later
        clinic_id=user.clinic_id if hasattr(user, 'clinic_id') else None
    )

    # Log upload
    AuditLogger.log(
        db=db,
        action="upload",
        resource_type="raw_audio",
        user_id=user.id,
        resource_id=lifecycle_metadata['file_id'],
        request=request,
        success=True,
        metadata={
            "filename": fn,
            "size_bytes": len(content),
            "scheduled_deletion": lifecycle_metadata['scheduled_deletion']
        }
    )

    # Transcribe (existing logic)
    # ...

    # Mark as processed
    manager.mark_processed(file_id=lifecycle_metadata['file_id'])

    return {
        "text": text,
        "audio_filename": fn,
        "file_id": lifecycle_metadata['file_id'],
        "scheduled_deletion": lifecycle_metadata['scheduled_deletion']
    }
```

### 5. Add Consent Tracking

Create new endpoint for consent:

```python
from pydantic import BaseModel

class ConsentCreate(BaseModel):
    patient_ref: str  # Patient MRN or anonymized ID
    consent_method: str  # "verbal", "written", "digital"
    notes: Optional[str] = None

@app.post("/consent")
def record_consent(
    payload: ConsentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = Request
):
    # Check permission
    if not RBACManager.has_permission(user.id, "write_patient_data", db):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Create consent record
    consent_id = f"CONSENT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"

    consent = ConsentRecord(
        consent_id=consent_id,
        doctor_id=user.id,
        patient_ref=payload.patient_ref,
        consent_method=payload.consent_method,
        consent_timestamp=datetime.utcnow(),
        consent_version="v1.0",
        withdrawn=False,
        notes=payload.notes
    )

    db.add(consent)
    db.commit()
    db.refresh(consent)

    # Log consent
    AuditLogger.log_consent_action(
        db=db,
        user_id=user.id,
        patient_ref=payload.patient_ref,
        action="consent_granted",
        consent_id=consent_id,
        request=request
    )

    return {"consent_id": consent_id, "message": "Consent recorded"}
```

### 6. Add Encryption for Sensitive Files (Optional)

If you want to encrypt files at rest:

```python
@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), ...):
    # Save temporary plaintext
    temp_path = Path(f"/tmp/{fn}")
    with open(temp_path, "wb") as f:
        f.write(content)

    # Encrypt before storing
    encrypted_path = Path("data_storage/raw_data") / f"{fn}.enc"

    em = EncryptionManager(clinic_id=user.clinic_id)
    encrypt_metadata = em.encrypt_file(
        input_path=temp_path,
        output_path=encrypted_path
    )

    # Delete temp plaintext
    temp_path.unlink()

    # Register encrypted file
    manager = LifecycleManager(db)
    lifecycle_metadata = manager.register_file(
        file_path=encrypted_path,
        file_type="raw_audio",
        user_id=user.id,
        ...
    )

    # Store nonce for later decryption
    # (Could add to DataLifecycleRecord or separate metadata table)

    # Transcribe from decrypted data
    decrypted_temp = Path(f"/tmp/decrypt_{fn}")
    em.decrypt_file(
        input_path=encrypted_path,
        output_path=decrypted_temp,
        nonce_b64=encrypt_metadata['nonce']
    )

    # Process decrypted file
    # ...

    # Delete decrypted temp
    decrypted_temp.unlink()
```

### 7. Create Initial Admin User

```python
# run_once_setup.py
from main import SessionLocal, User, hash_password
from security.rbac import RBACManager
import sys

def setup_admin():
    db = SessionLocal()

    # Check if admin exists
    admin = db.query(User).filter(User.email == "admin@dermtrack.local").first()

    if admin:
        print("Admin user already exists")
        return

    # Create admin
    admin = User(
        email="admin@dermtrack.local",
        password_hash=hash_password("change-me-immediately")
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Assign admin role
    RBACManager.assign_role(
        user_id=admin.id,
        role="admin",
        assigned_by=None,
        clinic_id="default",
        db=db
    )

    print(f"✓ Admin user created: {admin.email}")
    print(f"✓ Default password: change-me-immediately")
    print(f"✓ CHANGE THIS PASSWORD IMMEDIATELY!")

    db.close()

if __name__ == "__main__":
    setup_admin()
```

Run once:
```bash
python run_once_setup.py
```

### 8. Add Audit Log Viewing Endpoint (Admin Only)

```python
@app.get("/admin/audit-logs")
def get_audit_logs(
    limit: int = 100,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check admin permission
    if not RBACManager.has_permission(user.id, "read_audit_logs", db):
        raise HTTPException(status_code=403, detail="Admin access required")

    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    return [{
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "timestamp": log.timestamp.isoformat(),
        "ip_address": log.ip_address,
        "success": log.success,
        "error_message": log.error_message
    } for log in logs]
```

## Testing

### Test RBAC

```python
# test_rbac.py
from main import SessionLocal
from security.rbac import RBACManager

db = SessionLocal()

# Test permissions
user_id = 1  # Your test user
print(f"User {user_id} roles:", RBACManager.get_user_roles(user_id, db))
print(f"Can read patient data:", RBACManager.has_permission(user_id, "read_patient_data", db))
print(f"Can manage users:", RBACManager.has_permission(user_id, "manage_users", db))

db.close()
```

### Test Audit Logging

```python
# test_audit.py
from main import SessionLocal
from security.audit import AuditLogger

db = SessionLocal()

# Create test log
AuditLogger.log(
    db=db,
    action="test_action",
    resource_type="test_resource",
    user_id=1,
    resource_id="test_123",
    success=True,
    metadata={"test": "data"}
)

# Query logs
logs = db.query(AuditLog).filter(AuditLog.action == "test_action").all()
print(f"Found {len(logs)} test logs")

db.close()
```

### Test Lifecycle Management

```python
# test_lifecycle.py
from main import SessionLocal
from data_lifecycle import LifecycleManager
from pathlib import Path

db = SessionLocal()

# Create test file
test_file = Path("test_data.txt")
test_file.write_text("Test content")

# Register file
manager = LifecycleManager(db)
metadata = manager.register_file(
    file_path=test_file,
    file_type="processed_text",  # 30 day retention
    user_id=1,
    consultation_id=None
)

print(f"File registered: {metadata['file_id']}")
print(f"Scheduled deletion: {metadata['scheduled_deletion']}")

# Check status
status = manager.get_file_status(metadata['file_id'])
print(f"Days until deletion: {status['days_until_deletion']}")

# Clean up
test_file.unlink()
db.close()
```

### Test Automated Deletion

```bash
# Dry run (safe, doesn't delete)
python cron_jobs/auto_delete.py --dry-run

# Check what would be deleted
# If output looks correct, run live:
python cron_jobs/auto_delete.py --alert-email your@email.com
```

## Environment Variables

Add to `.env`:

```bash
# Security
ENCRYPTION_KEY=<generate-with-encryption-script>
SESSION_TIMEOUT_MINUTES=30

# Optional: Per-clinic keys
ENCRYPTION_KEY_CLINIC1=<key>
ENCRYPTION_KEY_CLINIC2=<key>

# Optional: Versioned keys for rotation
ENCRYPTION_KEY_CLINIC1_2025_01=<key>
ENCRYPTION_KEY_CLINIC1_2025_02=<key>
```

## Migration Checklist

- [ ] Run database migration to create security tables
- [ ] Generate encryption key(s)
- [ ] Set environment variables
- [ ] Create initial admin user
- [ ] Assign roles to existing users
- [ ] Update file upload endpoints to use lifecycle tracking
- [ ] Add RBAC checks to sensitive endpoints
- [ ] Add audit logging to all data access
- [ ] Set up automated deletion cron job
- [ ] Test in staging environment
- [ ] Update privacy policy and DPA with clinic information
- [ ] Train staff on consent procedures
- [ ] Deploy to production
- [ ] Monitor audit logs for issues

## Common Patterns

### Pattern 1: Protected Endpoint with Audit Logging

```python
@app.get("/resource/{id}")
def get_resource(
    id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = Request
):
    # 1. Check permission
    if not RBACManager.has_permission(user.id, "read_resource", db):
        AuditLogger.log_failed_access(db, user.id, "resource", str(id), "read", "Permission denied", request)
        raise HTTPException(status_code=403, detail="Permission denied")

    # 2. Fetch resource
    resource = db.query(Resource).filter(Resource.id == id).first()
    if not resource:
        raise HTTPException(status_code=404)

    # 3. Log successful access
    AuditLogger.log_data_access(db, user.id, "resource", str(id), "read", request)

    # 4. Return data
    return resource
```

### Pattern 2: File Upload with Lifecycle Tracking

```python
@app.post("/upload")
async def upload_file(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Save file
    file_path = Path(f"data_storage/raw_data/{file.filename}")
    content = await file.read()
    file_path.write_bytes(content)

    # 2. Register in lifecycle
    manager = LifecycleManager(db)
    metadata = manager.register_file(
        file_path=file_path,
        file_type="raw_audio",
        user_id=user.id
    )

    # 3. Return with deletion info
    return {
        "file_id": metadata['file_id'],
        "scheduled_deletion": metadata['scheduled_deletion'],
        "retention_days": metadata['retention_days']
    }
```

### Pattern 3: Consent Check Before Recording

```python
@app.post("/start-recording")
def start_recording(
    patient_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Check if valid consent exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    consent = db.query(ConsentRecord).filter(
        ConsentRecord.patient_ref == patient.mrn,
        ConsentRecord.withdrawn == False
    ).first()

    if not consent:
        raise HTTPException(
            status_code=403,
            detail="No valid consent on file. Please obtain consent before recording."
        )

    # 2. Proceed with recording
    return {"message": "Recording authorized", "consent_id": consent.consent_id}
```

## Need Help?

- **Documentation**: See `SECURITY_README.md`
- **Code Examples**: See inline comments in security modules
- **Issues**: Check audit logs for troubleshooting
