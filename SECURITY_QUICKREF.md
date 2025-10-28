# Security Quick Reference Card

## Setup (One-Time)

```bash
cd backend

# 1. Run setup script
python setup_security.py

# 2. Update .env with generated encryption key

# 3. Set up cron job for auto-deletion
crontab -e
# Add: 0 * * * * cd /path/to/DermTrack/backend && python cron_jobs/auto_delete.py --alert-email admin@clinic.com
```

## Data Retention Policy

| Data Type               | Retention | Auto-Delete |
|-------------------------|-----------|-------------|
| Raw audio/video         | 24 hours  | ✓ Yes       |
| Processed transcripts   | 30 days   | ✓ Yes       |
| Anonymized training     | 5 years   | ✓ Yes       |
| Consent records         | 7 years   | ✗ No        |
| Audit logs              | 7 years   | ✗ No        |

## Roles & Permissions

| Feature                | Doctor | Admin | Developer | Auditor |
|------------------------|--------|-------|-----------|---------|
| Read patient data      | ✓      | ✓     | ✗         | ✗       |
| Write patient data     | ✓      | ✗     | ✗         | ✗       |
| Access raw recordings  | ✓      | ✓     | ✗         | ✗       |
| View audit logs        | ✗      | ✓     | ✗         | ✓       |
| Manage users           | ✗      | ✓     | ✗         | ✗       |
| Access anonymized data | ✗      | ✓     | ✓         | ✓       |

## Code Snippets

### Check Permission

```python
from security.rbac import RBACManager

if not RBACManager.has_permission(user.id, "read_patient_data", db):
    raise HTTPException(status_code=403, detail="Permission denied")
```

### Log Access

```python
from security.audit import AuditLogger

AuditLogger.log_data_access(
    db=db,
    user_id=user.id,
    resource_type="patient",
    resource_id=str(patient_id),
    action="read",
    request=request
)
```

### Register File for Auto-Deletion

```python
from data_lifecycle import LifecycleManager

manager = LifecycleManager(db)
metadata = manager.register_file(
    file_path=Path("audio.wav"),
    file_type="raw_audio",  # 24h retention
    user_id=user.id
)
# File will auto-delete after 24 hours
```

### Record Consent

```python
from security_models import ConsentRecord

consent = ConsentRecord(
    consent_id=f"CONSENT_{timestamp}_{token_hex(4)}",
    doctor_id=user.id,
    patient_ref=patient.mrn,
    consent_method="verbal",
    consent_timestamp=datetime.utcnow(),
    consent_version="v1.0",
    withdrawn=False
)
db.add(consent)
db.commit()
```

### Encrypt File

```python
from security.encryption import EncryptionManager

em = EncryptionManager(clinic_id="clinic1")
metadata = em.encrypt_file(
    input_path=Path("plaintext.dat"),
    output_path=Path("encrypted.dat.enc")
)
# Store metadata['nonce'] for decryption
```

## Environment Variables

```bash
# Required
ENCRYPTION_KEY=<base64-encoded-32-byte-key>
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dermtrack

# Optional
SESSION_TIMEOUT_MINUTES=30
ENCRYPTION_KEY_CLINIC1=<key>
ENCRYPTION_KEY_CLINIC2=<key>
```

## Manual Tasks

### Run Auto-Deletion Manually

```bash
# Dry run (safe, just shows what would be deleted)
python cron_jobs/auto_delete.py --dry-run

# Live run
python cron_jobs/auto_delete.py --alert-email admin@clinic.com
```

### Assign Role to User

```python
from security.rbac import RBACManager

RBACManager.assign_role(
    user_id=123,
    role="doctor",  # or "admin", "developer", "auditor"
    assigned_by=admin_user_id,
    clinic_id="clinic1",
    db=db
)
```

### View Audit Logs

```python
from security.audit import AuditLogger

# Get user activity
logs = AuditLogger.get_user_audit_trail(db, user_id=123, limit=100)

# Get resource access history
logs = AuditLogger.get_resource_audit_trail(db, "patient", "456", limit=50)

# Get failed access attempts
logs = AuditLogger.get_failed_access_attempts(db, since_hours=24)
```

### Check File Status

```python
from data_lifecycle import LifecycleManager

manager = LifecycleManager(db)
status = manager.get_file_status(file_id="raw_audio_20250128_abc123")

print(f"Days until deletion: {status['days_until_deletion']}")
print(f"Is deleted: {status['is_deleted']}")
```

## File Structure

```
backend/
├── data_storage/              # NOT in git!
│   ├── raw_data/              # 24h retention
│   ├── processed_data/        # 30d retention
│   ├── metadata/              # Permanent
│   └── audit_logs/            # 7y retention
├── security/
│   ├── encryption/            # AES-256-GCM
│   ├── rbac/                  # Role-based access
│   └── audit/                 # Audit logging
├── cron_jobs/
│   └── auto_delete.py         # Scheduled deletion
├── legal_templates/
│   ├── PRIVACY_POLICY.md
│   └── DATA_PROCESSING_AGREEMENT.md
├── security_models.py         # DB schema
├── data_lifecycle.py          # Lifecycle management
├── setup_security.py          # One-time setup
└── INTEGRATION_GUIDE.md       # How to integrate
```

## Compliance Checklist

- ✓ AES-256-GCM encryption at rest
- ✓ TLS 1.3 in transit
- ✓ Per-clinic encryption keys, monthly rotation
- ✓ RBAC with 4 roles
- ✓ Comprehensive audit logging (7 years)
- ✓ Automatic deletion (24h for raw data)
- ✓ Consent management
- ✓ Session timeout (30 min)
- ✓ Data segregation
- ✓ Checksum verification
- ✓ Developer access restrictions
- ✓ Privacy policy template
- ✓ Data Processing Agreement template

## Troubleshooting

**"No encryption key found"**
→ Run: `python security/encryption/__init__.py` and add to `.env`

**"Permission denied"**
→ Check roles: `RBACManager.get_user_roles(user_id, db)`

**Files not auto-deleting**
→ Check cron: `crontab -l` and logs: `/var/log/dermtrack/auto_delete.log`

**Hash mismatch on deletion**
→ File was tampered! Check audit logs for unauthorized access.

## Support

**Documentation**: `SECURITY_README.md`, `INTEGRATION_GUIDE.md`
**Security Questions**: security@dermtrack.com
**Legal Templates**: `legal_templates/`

---
**DermTrack Security v1.0** | Protecting Patient Privacy
