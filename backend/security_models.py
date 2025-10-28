"""
Security-focused database models for medical data handling.
Implements consent management, audit logging, RBAC, and data lifecycle tracking.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from main import Base
import enum


# ============================================================================
# RBAC (Role-Based Access Control)
# ============================================================================

class UserRole(str, enum.Enum):
    """User roles with different access levels"""
    DOCTOR = "doctor"
    ADMIN = "admin"
    DEVELOPER = "developer"
    AUDITOR = "auditor"


class UserRoleAssignment(Base):
    """Maps users to roles for RBAC"""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(Enum(UserRole), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # who granted this role
    clinic_id = Column(String(255), nullable=True, index=True)  # for multi-clinic setups
    is_active = Column(Boolean, default=True, nullable=False)


# ============================================================================
# Consent Management
# ============================================================================

class ConsentRecord(Base):
    """Stores patient consent for data processing and recording"""
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    consent_id = Column(String(255), unique=True, nullable=False, index=True)  # unique identifier
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    patient_ref = Column(String(255), nullable=False, index=True)  # de-identified patient reference
    consent_method = Column(String(100), nullable=False)  # e.g., "verbal", "written", "digital"
    consent_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    consent_version = Column(String(50), nullable=False)  # version of consent form/policy
    withdrawn = Column(Boolean, default=False, nullable=False, index=True)
    withdrawn_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    doctor = relationship("User", foreign_keys=[doctor_id])


# ============================================================================
# Audit Logging
# ============================================================================

class AuditLog(Base):
    """Comprehensive audit trail for all data access and operations"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # nullable for system events
    action = Column(String(255), nullable=False, index=True)  # e.g., "read", "write", "delete", "export"
    resource_type = Column(String(100), nullable=False, index=True)  # e.g., "audio", "transcript", "note"
    resource_id = Column(String(255), nullable=True, index=True)  # ID of the accessed resource
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(512), nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    additional_metadata = Column(Text, nullable=True)  # JSON string for additional context

    # Relationships
    user = relationship("User", foreign_keys=[user_id])


# ============================================================================
# Data Lifecycle Tracking
# ============================================================================

class DataLifecycleRecord(Base):
    """Tracks lifecycle of sensitive data files for compliance and auto-deletion"""
    __tablename__ = "data_lifecycle"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(255), unique=True, nullable=False, index=True)  # unique file identifier
    file_type = Column(String(50), nullable=False, index=True)  # "raw_audio", "raw_video", "processed_text", etc.
    file_path = Column(String(1024), nullable=False)  # relative path in data_storage
    file_hash = Column(String(128), nullable=False)  # SHA-256 hash for integrity

    # Lifecycle timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    scheduled_deletion = Column(DateTime, nullable=False, index=True)  # when to delete
    deleted_at = Column(DateTime, nullable=True, index=True)

    # Ownership and metadata
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)
    clinic_id = Column(String(255), nullable=True, index=True)
    encryption_key_version = Column(String(50), nullable=True)  # for key rotation tracking

    # Status
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deletion_verified = Column(Boolean, default=False, nullable=False)  # verified via hash check

    # Relationships
    user = relationship("User", foreign_keys=[user_id])


# ============================================================================
# Encryption Key Management
# ============================================================================

class EncryptionKeyMetadata(Base):
    """Tracks encryption keys for rotation and audit purposes (stores metadata only, not keys!)"""
    __tablename__ = "encryption_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(255), unique=True, nullable=False, index=True)
    clinic_id = Column(String(255), nullable=False, index=True)  # separate keys per clinic
    key_version = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    rotated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)  # monthly rotation
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    algorithm = Column(String(50), nullable=False, default="AES-256-GCM")
    key_storage_location = Column(String(255), nullable=False)  # e.g., "env", "vault", "kms"
    notes = Column(Text, nullable=True)


# ============================================================================
# Session Management (for timeout tracking)
# ============================================================================

class UserSession(Base):
    """Tracks active user sessions for security and timeout enforcement"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(512), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
