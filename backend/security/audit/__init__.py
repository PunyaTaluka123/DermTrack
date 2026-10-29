"""
Comprehensive audit logging system for medical data access and operations.
Logs every access with user_id, action, timestamp, resource, and IP.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import json
from fastapi import Request
from sqlalchemy.orm import Session


class AuditLogger:
    """
    Centralized audit logging for compliance and security monitoring.

    Logs include:
    - User ID and action performed
    - Resource type and ID accessed
    - Timestamp (UTC)
    - IP address and user agent
    - Success/failure status
    - Additional metadata
    """

    @staticmethod
    def log(
        db: Session,
        action: str,
        resource_type: str,
        user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        request: Optional[Request] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log an action to the audit trail.

        Args:
            db: Database session
            action: Action performed (e.g., "read", "write", "delete", "export")
            resource_type: Type of resource (e.g., "audio", "transcript", "note")
            user_id: ID of user performing action (None for system events)
            resource_id: ID of the accessed resource
            request: FastAPI request object (for IP and user agent)
            success: Whether the action succeeded
            error_message: Error message if action failed
            metadata: Additional context as dict (will be JSON serialized)
        """
        from security_models import AuditLog

        # Extract IP and user agent from request
        ip_address = None
        user_agent = None
        if request:
            # Get IP from X-Forwarded-For header (proxy) or direct connection
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip_address = forwarded_for.split(",")[0].strip()
            else:
                ip_address = request.client.host if request.client else None

            user_agent = request.headers.get("User-Agent")

        # Serialize metadata to JSON
        metadata_json = None
        if metadata:
            try:
                metadata_json = json.dumps(metadata)
            except Exception:
                metadata_json = str(metadata)

        # Create audit log entry
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            additional_metadata=metadata_json
        )

        db.add(log_entry)
        db.commit()

        return log_entry

    @staticmethod
    def log_data_access(
        db: Session,
        user_id: int,
        resource_type: str,
        resource_id: str,
        action: str,
        request: Optional[Request] = None
    ):
        """Convenience method for logging data access"""
        return AuditLogger.log(
            db=db,
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            request=request,
            success=True
        )

    @staticmethod
    def log_data_modification(
        db: Session,
        user_id: int,
        resource_type: str,
        resource_id: str,
        action: str,
        changes: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Convenience method for logging data modifications with change tracking"""
        return AuditLogger.log(
            db=db,
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            request=request,
            success=True,
            metadata={"changes": changes} if changes else None
        )

    @staticmethod
    def log_failed_access(
        db: Session,
        user_id: Optional[int],
        resource_type: str,
        resource_id: Optional[str],
        action: str,
        error: str,
        request: Optional[Request] = None
    ):
        """Convenience method for logging failed access attempts"""
        return AuditLogger.log(
            db=db,
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            request=request,
            success=False,
            error_message=error
        )

    @staticmethod
    def log_deletion(
        db: Session,
        user_id: Optional[int],
        resource_type: str,
        resource_id: str,
        file_hash: str,
        reason: str = "scheduled_deletion",
        request: Optional[Request] = None
    ):
        """
        Log data deletion with hash for verification.

        This is critical for compliance - we need proof that data was actually deleted.
        """
        return AuditLogger.log(
            db=db,
            action="delete",
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            request=request,
            success=True,
            metadata={
                "file_hash": file_hash,
                "reason": reason,
                "deleted_at": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def log_export(
        db: Session,
        user_id: int,
        resource_type: str,
        resource_ids: list,
        export_format: str,
        request: Optional[Request] = None
    ):
        """Log data export operations"""
        return AuditLogger.log(
            db=db,
            action="export",
            resource_type=resource_type,
            user_id=user_id,
            resource_id=None,
            request=request,
            success=True,
            metadata={
                "resource_count": len(resource_ids),
                "resource_ids": resource_ids[:100],  # Limit to first 100 IDs
                "export_format": export_format
            }
        )

    @staticmethod
    def log_consent_action(
        db: Session,
        user_id: int,
        patient_ref: str,
        action: str,
        consent_id: str,
        request: Optional[Request] = None
    ):
        """Log consent-related actions (granted, withdrawn, updated)"""
        return AuditLogger.log(
            db=db,
            action=action,
            resource_type="consent",
            user_id=user_id,
            resource_id=consent_id,
            request=request,
            success=True,
            metadata={"patient_ref": patient_ref}
        )

    @staticmethod
    def get_user_audit_trail(db: Session, user_id: int, limit: int = 100):
        """Get audit trail for a specific user"""
        from security_models import AuditLog

        return db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()

    @staticmethod
    def get_resource_audit_trail(db: Session, resource_type: str, resource_id: str, limit: int = 100):
        """Get audit trail for a specific resource"""
        from security_models import AuditLog

        return db.query(AuditLog).filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        ).order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()

    @staticmethod
    def get_failed_access_attempts(db: Session, since_hours: int = 24, limit: int = 100):
        """Get failed access attempts for security monitoring"""
        from security_models import AuditLog
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(hours=since_hours)

        return db.query(AuditLog).filter(
            AuditLog.success == False,
            AuditLog.timestamp >= since
        ).order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()


# Decorator for automatic audit logging
def audit_action(action: str, resource_type: str):
    """
    Decorator to automatically log actions.

    Usage:
        @app.get("/patient/{id}")
        @audit_action("read", "patient")
        def get_patient(id: int, user = Depends(get_current_user), db = Depends(get_db), request: Request):
            ...
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            db = kwargs.get('db')
            request = kwargs.get('request')

            # Get resource ID from kwargs if present
            resource_id = kwargs.get('id') or kwargs.get('patient_id') or kwargs.get('note_id')

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Log successful action
                if user and db:
                    AuditLogger.log(
                        db=db,
                        action=action,
                        resource_type=resource_type,
                        user_id=user.id,
                        resource_id=str(resource_id) if resource_id else None,
                        request=request,
                        success=True
                    )

                return result

            except Exception as e:
                # Log failed action
                if user and db:
                    AuditLogger.log(
                        db=db,
                        action=action,
                        resource_type=resource_type,
                        user_id=user.id if user else None,
                        resource_id=str(resource_id) if resource_id else None,
                        request=request,
                        success=False,
                        error_message=str(e)
                    )

                # Re-raise exception
                raise

        return wrapper

    return decorator
