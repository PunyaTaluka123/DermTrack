# DermTrack Security Infrastructure

## Overview

This document describes the comprehensive security infrastructure for DermTrack, a HIPAA-compliant medical data handling system for doctor-patient conversation recording and transcription.

**Last Updated**: [DATE]
**Security Version**: 1.0

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Data Segregation](#data-segregation)
3. [Encryption](#encryption)
4. [Role-Based Access Control (RBAC)](#role-based-access-control)
5. [Audit Logging](#audit-logging)
6. [Data Lifecycle Management](#data-lifecycle-management)
7. [Consent Management](#consent-management)
8. [Automated Deletion](#automated-deletion)
9. [Setup Instructions](#setup-instructions)
10. [Compliance](#compliance)

---

## Architecture Overview

DermTrack implements defense-in-depth security with multiple layers:

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                           │
│  (Doctors, Admins, Developers, Auditors)                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    RBAC Middleware                          │
│  • Role verification                                        │
│  • Permission checks                                        │
│  • Session timeout (30 min)                                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Audit Logging Layer                       │
│  • Log all access (user, timestamp, IP, action)             │
│  • Tamper-evident logs                                      │
│  • 7-year retention                                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Encryption Layer                           │
│  • AES-256-GCM at rest                                      │
│  • TLS 1.3 in transit                                       │
│  • Per-clinic keys, monthly rotation                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Storage Layer                         │
│  • raw_data/ (temp, 24h)                                    │
│  • processed_data/ (temp, 30d)                              │
│  • metadata/ (permanent)                                    │
│  • audit_logs/ (7y)                                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│             Lifecycle Management & Auto-Deletion            │
│  • Track all files                                          │
│  • Calculate deletion dates                                 │
│  • Verify checksums                                         │
│  • Automated cron deletion                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Segregation

### Folder Structure

```
backend/
├── data_storage/                 # Sensitive data (NOT in git)
│   ├── raw_data/                 # Raw audio/video (24h retention)
│   ├── processed_data/           # Transcripts (30d retention)
│   ├── metadata/                 # File metadata, checksums
│   └── audit_logs/               # Audit trail (7y retention)
│
├── security/                     # Security modules
│   ├── encryption/               # AES-256 encryption utilities
│   ├── rbac/                     # Role-based access control
│   └── audit/                    # Audit logging system
│
├── cron_jobs/                    # Automated tasks
│   └── auto_delete.py            # Scheduled deletion job
│
└── legal_templates/              # Policy templates
    ├── PRIVACY_POLICY.md
    └── DATA_PROCESSING_AGREEMENT.md
```

### Database Segregation

**Clinical Data Tables** (main.py):
- `users` - Doctor/clinic accounts
- `patients` - Patient demographics
- `consultations` - Consultation records
- `notes` - Clinical notes

**Security Tables** (security_models.py):
- `user_roles` - RBAC role assignments
- `consent_records` - Patient consent tracking
- `audit_logs` - Comprehensive audit trail
- `data_lifecycle` - File lifecycle tracking
- `encryption_keys` - Key rotation metadata
- `user_sessions` - Session management

---

## Encryption

### At Rest: AES-256-GCM

**Implementation**: `backend/security/encryption/__init__.py`

**Features**:
- 256-bit AES encryption in GCM mode (authenticated encryption)
- Separate keys per clinic for data isolation
- Monthly key rotation support
- Never hardcodes keys - always from environment variables
- SHA-256 checksums for integrity verification

**Key Management**:
```bash
# Generate a new encryption key
python backend/security/encryption/__init__.py

# Set in environment (.env file)
ENCRYPTION_KEY=<base64-encoded-32-byte-key>

# Clinic-specific key (recommended for multi-tenant)
ENCRYPTION_KEY_CLINIC1=<key>
ENCRYPTION_KEY_CLINIC2=<key>

# Versioned key for rotation
ENCRYPTION_KEY_CLINIC1_2025_01=<key>
ENCRYPTION_KEY_CLINIC1_2025_02=<key>
```

**Usage**:
```python
from security.encryption import EncryptionManager

# Initialize for specific clinic
em = EncryptionManager(clinic_id="clinic1")

# Encrypt file
metadata = em.encrypt_file(
    input_path=Path("audio.wav"),
    output_path=Path("data_storage/raw_data/audio.enc")
)
# Returns: {nonce, checksum_plaintext, checksum_ciphertext, key_version}

# Decrypt file
em.decrypt_file(
    input_path=Path("data_storage/raw_data/audio.enc"),
    output_path=Path("audio.wav"),
    nonce_b64=metadata['nonce'],
    verify_checksum=metadata['checksum_plaintext']
)
```

### In Transit: TLS 1.3

- All API endpoints use HTTPS only
- Minimum TLS version: 1.3
- Strong cipher suites only
- Certificate pinning recommended for mobile apps

---

## Role-Based Access Control

### Roles and Permissions

**Implementation**: `backend/security/rbac/__init__.py`

| Role      | Read Own Data | Write Data | Read Raw Audio | Read Audit Logs | Manage Users | Access Anonymized |
|-----------|---------------|------------|----------------|-----------------|--------------|-------------------|
| Doctor    | ✓             | ✓          | ✓              | ✗               | ✗            | ✗                 |
| Admin     | ✓             | ✗          | ✓              | ✓               | ✓            | ✓                 |
| Developer | ✗             | ✗          | ✗              | ✗               | ✗            | ✓ (only)          |
| Auditor   | ✗             | ✗          | ✗              | ✓               | ✗            | ✓                 |

**Key Principle**: Developers have NO access to raw recordings or identifiable patient data.

### Assigning Roles

```python
from security.rbac import RBACManager

# Assign role to user
RBACManager.assign_role(
    user_id=123,
    role="doctor",
    assigned_by=admin_user_id,
    clinic_id="clinic1",
    db=db
)

# Check permission
has_perm = RBACManager.has_permission(
    user_id=123,
    permission="read_raw_audio",
    db=db
)
```

### Route Protection

```python
from security.rbac import require_permission, require_role

@app.get("/patient/{id}")
@require_permission("read_patient_data")
def get_patient(id: int, user = Depends(get_current_user), db = Depends(get_db)):
    # Only users with "read_patient_data" permission can access
    pass

@app.get("/admin/audit-logs")
@require_role("auditor")
def get_audit_logs(user = Depends(get_current_user), db = Depends(get_db)):
    # Only users with "auditor" role can access
    pass
```

### Session Timeout

- **Idle timeout**: 30 minutes (configurable via `SESSION_TIMEOUT_MINUTES`)
- **Absolute timeout**: 12 hours
- Automatic logout on timeout
- Session activity tracked in `user_sessions` table

---

## Audit Logging

### What We Log

**Implementation**: `backend/security/audit/__init__.py`

**Every data access includes**:
- `user_id` - Who accessed the data
- `action` - What they did (read, write, delete, export)
- `resource_type` - What type of data (audio, transcript, note, consent)
- `resource_id` - Specific resource identifier
- `timestamp` - When it happened (UTC)
- `ip_address` - Where they accessed from
- `user_agent` - What client/browser
- `success` - Whether action succeeded or failed
- `metadata` - Additional context (JSON)

### Usage

```python
from security.audit import AuditLogger

# Log data access
AuditLogger.log_data_access(
    db=db,
    user_id=user.id,
    resource_type="audio",
    resource_id="audio_123",
    action="read",
    request=request
)

# Log deletion
AuditLogger.log_deletion(
    db=db,
    user_id=None,  # System action
    resource_type="raw_audio",
    resource_id="audio_123",
    file_hash="sha256:abc123...",
    reason="scheduled_deletion"
)

# Log failed access
AuditLogger.log_failed_access(
    db=db,
    user_id=user.id,
    resource_type="patient",
    resource_id="patient_456",
    action="read",
    error="Permission denied",
    request=request
)
```

### Decorator for Automatic Logging

```python
from security.audit import audit_action

@app.get("/patient/{id}")
@audit_action("read", "patient")
def get_patient(id: int, user = Depends(get_current_user), db = Depends(get_db), request: Request):
    # Access automatically logged
    pass
```

### Retention

- **Audit logs**: Retained for 7 years (legal requirement)
- **Never deleted**: Even when user account is deleted
- **Tamper-evident**: Append-only logs with checksums

---

## Data Lifecycle Management

### Retention Policies

**Implementation**: `backend/data_lifecycle.py`

| Data Type               | Retention Period | Auto-Delete |
|-------------------------|------------------|-------------|
| Raw audio/video         | 24 hours         | ✓ Yes       |
| Processed transcripts   | 30 days          | ✓ Yes       |
| Anonymized training data| 5 years          | ✓ Yes       |
| Consent records         | 7 years          | ✗ No        |
| Audit logs              | 7 years          | ✗ No        |

### Lifecycle Stages

```
1. UPLOAD
   ↓
   • Calculate SHA-256 checksum
   • Store metadata in data_lifecycle table
   • Calculate scheduled_deletion date

2. PROCESS
   ↓
   • Update processed_at timestamp
   • Maintain hash integrity

3. RETURN OUTPUT
   ↓
   • Deliver results to authorized user
   • Log access in audit trail

4. AUTO-DELETE
   ↓
   • Verify file hash (detect tampering)
   • Delete file from storage
   • Log deletion with hash and timestamp
   • Mark as deleted in data_lifecycle table
```

### Usage

```python
from data_lifecycle import LifecycleManager, DataRetentionPolicy

manager = LifecycleManager(db)

# Register new file
metadata = manager.register_file(
    file_path=Path("media/audio/recording.wav"),
    file_type="raw_audio",  # Triggers 24h retention
    user_id=user.id,
    consultation_id=consultation.id,
    clinic_id="clinic1"
)

# Mark as processed
manager.mark_processed(file_id=metadata['file_id'])

# Check file status
status = manager.get_file_status(file_id=metadata['file_id'])
# Returns: {file_id, file_hash, uploaded_at, scheduled_deletion, is_deleted, days_until_deletion}

# Manual deletion
result = manager.delete_file(file_id=metadata['file_id'], verify_hash=True)
# Returns: {file_id, file_hash, deleted_at, verified}
```

---

## Consent Management

### Consent Metadata Structure

**Implementation**: `security_models.py` → `ConsentRecord`

```python
class ConsentRecord:
    consent_id          # Unique identifier (e.g., "CONSENT_20250128_ABC123")
    doctor_id           # Doctor who obtained consent
    patient_ref         # De-identified patient reference
    consent_method      # "verbal", "written", "digital"
    consent_timestamp   # When consent was obtained
    consent_version     # Version of consent policy
    withdrawn           # Boolean: is consent withdrawn?
    withdrawn_at        # Timestamp of withdrawal
    notes               # Additional context
```

### Obtaining Consent

```python
from security_models import ConsentRecord
from datetime import datetime

# Record consent
consent = ConsentRecord(
    consent_id=f"CONSENT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{token_hex(4)}",
    doctor_id=doctor.id,
    patient_ref=patient.mrn,  # Or anonymized ID
    consent_method="verbal",
    consent_timestamp=datetime.utcnow(),
    consent_version="v1.0",
    withdrawn=False,
    notes="Patient verbally consented at start of consultation"
)
db.add(consent)
db.commit()

# Log consent action in audit trail
AuditLogger.log_consent_action(
    db=db,
    user_id=doctor.id,
    patient_ref=patient.mrn,
    action="consent_granted",
    consent_id=consent.consent_id,
    request=request
)
```

### Withdrawing Consent

```python
# Withdraw consent
consent = db.query(ConsentRecord).filter(ConsentRecord.consent_id == consent_id).first()
consent.withdrawn = True
consent.withdrawn_at = datetime.utcnow()
db.commit()

# Log withdrawal
AuditLogger.log_consent_action(
    db=db,
    user_id=doctor.id,
    patient_ref=consent.patient_ref,
    action="consent_withdrawn",
    consent_id=consent.consent_id,
    request=request
)

# Trigger immediate deletion of patient data
# (implementation depends on business requirements)
```

### Consent Storage

- **Separate from clinical data**: Consent records stored in dedicated table
- **No PHI in consent record**: Uses de-identified patient reference
- **Immutable**: Original consent record never modified (only withdrawal flag)
- **7-year retention**: Legal requirement for consent records

---

## Automated Deletion

### Cron Job

**Implementation**: `backend/cron_jobs/auto_delete.py`

**Features**:
- Runs on schedule (recommended: hourly)
- Verifies file checksums before deletion
- Logs every deletion with hash
- Sends alert email on completion
- Dry-run mode for testing

### Setup

```bash
# Make executable
chmod +x backend/cron_jobs/auto_delete.py

# Test with dry-run
python backend/cron_jobs/auto_delete.py --dry-run

# Run live deletion
python backend/cron_jobs/auto_delete.py --alert-email admin@clinic.com
```

### Crontab Configuration

```bash
# Edit crontab
crontab -e

# Add entry (runs every hour)
0 * * * * cd /path/to/DermTrack/backend && /usr/bin/python3 cron_jobs/auto_delete.py --alert-email admin@clinic.com >> /var/log/dermtrack/auto_delete.log 2>&1
```

### Alert Email

Upon completion, sends email with:
- Total files checked
- Successfully deleted count
- Failed deletions (with errors)
- Execution timestamp
- Success/failure status

Example output:
```
DermTrack Automated Deletion Report
====================================

Execution Time: 2025-01-28T15:00:00Z

Summary:
--------
Total files checked: 47
Successfully deleted: 47
Failed deletions: 0

Status: SUCCESS
```

### Checksum Verification

Before deletion:
1. Calculate current SHA-256 hash of file
2. Compare with hash stored at upload time
3. If mismatch → File tampered with → Log error, do NOT delete
4. If match → Proceed with deletion
5. Log deletion with original hash for audit

---

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend

# Install Python packages
pip install -r requirements.txt

# Additional security packages
pip install cryptography==41.0.7 python-jose[cryptography]==3.3.0
```

### 2. Generate Encryption Key

```bash
# Generate key
python security/encryption/__init__.py

# Output:
# Generating new AES-256 encryption key...
#
# New encryption key (base64-encoded):
# kFz8PqR3tVwY1aB2cD4eF5gH6iJ7kL8mN9oP0qR1sT2u=
#
# Add this to your .env file:
# ENCRYPTION_KEY=kFz8PqR3tVwY1aB2cD4eF5gH6iJ7kL8mN9oP0qR1sT2u=
```

### 3. Configure Environment

Edit `.env`:
```bash
# Security settings
ENCRYPTION_KEY=<your-generated-key>
SESSION_TIMEOUT_MINUTES=30
SECURE_COOKIES=true

# Database (must use PostgreSQL for production)
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/dermtrack

# Session settings
ACCESS_TOKEN_EXPIRE_MINUTES=30  # Token lifetime
SESSION_COOKIE_SAMESITE=strict
```

### 4. Initialize Database

```bash
# This will create all tables including security tables
python -c "
from main import init_db
from security_models import Base
from main import engine
Base.metadata.create_all(bind=engine)
init_db()
print('Database initialized with security tables')
"
```

### 5. Create Admin User with Roles

```python
from main import SessionLocal, User, hash_password
from security.rbac import RBACManager

db = SessionLocal()

# Create admin user
admin = User(
    email="admin@clinic.com",
    password_hash=hash_password("secure-password")
)
db.add(admin)
db.commit()

# Assign admin role
RBACManager.assign_role(
    user_id=admin.id,
    role="admin",
    assigned_by=None,  # First admin
    clinic_id="clinic1",
    db=db
)

print(f"Admin user created: {admin.email}")
```

### 6. Set Up Cron Job

```bash
# Set up log directory
sudo mkdir -p /var/log/dermtrack
sudo chown $USER:$USER /var/log/dermtrack

# Add to crontab
crontab -e

# Add this line (runs hourly):
0 * * * * cd /path/to/DermTrack/backend && /usr/bin/python3 cron_jobs/auto_delete.py --alert-email admin@clinic.com >> /var/log/dermtrack/auto_delete.log 2>&1
```

### 7. Verify Setup

```bash
# Test encryption
python -c "
from security.encryption import EncryptionManager
from pathlib import Path

em = EncryptionManager()
print('✓ Encryption key loaded successfully')
print(f'✓ Key version: {em.key_version}')
"

# Test RBAC
python -c "
from security.rbac import RBACManager
from main import SessionLocal

db = SessionLocal()
print('✓ RBAC system initialized')
"

# Test audit logging
python -c "
from security.audit import AuditLogger
from main import SessionLocal

db = SessionLocal()
AuditLogger.log(db, 'system_test', 'system', success=True)
print('✓ Audit logging working')
"

# Dry-run deletion
python cron_jobs/auto_delete.py --dry-run
```

---

## Compliance

### HIPAA Compliance

✓ **Access Controls**: RBAC with 4 roles, session timeout
✓ **Audit Trails**: Comprehensive logging of all access
✓ **Encryption**: AES-256-GCM at rest, TLS 1.3 in transit
✓ **Data Minimization**: Automatic deletion after retention period
✓ **Breach Notification**: Audit logs enable incident detection
✓ **Business Associate Agreements**: DPA template provided

### GDPR Compliance

✓ **Right to Access**: Query audit logs, retrieve data
✓ **Right to Erasure**: Manual deletion before retention period
✓ **Right to Portability**: Export in machine-readable format
✓ **Data Protection by Design**: Security built into architecture
✓ **Consent Management**: Dedicated consent tracking system
✓ **Lawful Basis**: Processing based on explicit consent
✓ **International Transfers**: Standard Contractual Clauses in DPA

### Documentation

Legal templates provided:
- `legal_templates/PRIVACY_POLICY.md` - User-facing privacy policy
- `legal_templates/DATA_PROCESSING_AGREEMENT.md` - Clinic contracts

---

## Security Best Practices

### DO

✓ Use separate encryption keys per clinic
✓ Rotate keys monthly (update environment variable)
✓ Review audit logs regularly for suspicious activity
✓ Test automated deletion in dry-run mode first
✓ Keep consent records for full 7-year retention period
✓ Use HTTPS only (TLS 1.3 minimum)
✓ Enable MFA for admin accounts
✓ Conduct regular security audits

### DON'T

✗ Hardcode encryption keys in code
✗ Grant developers access to raw patient data
✗ Disable audit logging
✗ Skip checksum verification before deletion
✗ Delete audit logs or consent records prematurely
✗ Use SQLite in production (use PostgreSQL)
✗ Bypass RBAC checks in code
✗ Store keys in version control

---

## Troubleshooting

### "No encryption key found"

**Problem**: `ENCRYPTION_KEY` not set in environment

**Solution**:
```bash
# Generate key
python security/encryption/__init__.py

# Add to .env
echo "ENCRYPTION_KEY=<generated-key>" >> .env

# Restart application
```

### "Permission denied" errors

**Problem**: User lacks required role/permission

**Solution**:
```python
# Check user roles
from security.rbac import RBACManager
roles = RBACManager.get_user_roles(user_id, db)
print(f"User roles: {roles}")

# Assign missing role
RBACManager.assign_role(user_id, "doctor", admin_id, "clinic1", db)
```

### Automated deletion not running

**Problem**: Cron job not executing

**Solution**:
```bash
# Check cron logs
grep CRON /var/log/syslog

# Test manually
python backend/cron_jobs/auto_delete.py --dry-run

# Verify crontab
crontab -l
```

### Hash mismatch on deletion

**Problem**: File modified after upload (security issue!)

**Solution**:
```bash
# Check audit logs for unauthorized access
SELECT * FROM audit_logs
WHERE resource_id = 'file_123'
ORDER BY timestamp DESC;

# Investigate:
# - Who accessed the file?
# - When was it modified?
# - Was there a breach?

# DO NOT delete file until investigation complete
```

---

## Support

For security questions or issues:

**Email**: security@dermtrack.com
**Documentation**: See this README and code comments
**Audit Logs**: Check `audit_logs` table for access history

---

## Version History

| Version | Date       | Changes                                      |
|---------|------------|----------------------------------------------|
| 1.0     | 2025-01-28 | Initial security infrastructure release      |

---

**DermTrack Security Infrastructure v1.0**
**Protecting Patient Privacy, One Consultation at a Time**
