"""
Role-Based Access Control (RBAC) middleware for DermTrack.
Implements fine-grained access control for medical data.
"""

from fastapi import HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from functools import wraps
from datetime import datetime, timedelta
import os


# Import from main (will be available when integrated)
# from main import get_db, get_current_user, User
# from security_models import UserRole, UserRoleAssignment


class PermissionDenied(HTTPException):
    """Custom exception for permission denied"""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=403, detail=detail)


class RBACManager:
    """
    Manages role-based access control for DermTrack.

    Roles:
    - DOCTOR: Can access patient data, create consultations, view own data
    - ADMIN: Can manage users, view audit logs, configure system
    - DEVELOPER: Can view anonymized data, no access to raw/identifiable data
    - AUDITOR: Read-only access to audit logs and compliance data
    """

    # Define permissions for each role
    ROLE_PERMISSIONS = {
        "doctor": {
            "read_own_data": True,
            "write_own_data": True,
            "read_patient_data": True,
            "write_patient_data": True,
            "read_raw_audio": True,
            "write_raw_audio": True,
            "export_data": True,
            "read_audit_logs": False,
            "manage_users": False,
            "access_anonymized_data": False,
        },
        "admin": {
            "read_own_data": True,
            "write_own_data": True,
            "read_patient_data": True,
            "write_patient_data": False,  # Admins don't modify clinical data
            "read_raw_audio": True,
            "write_raw_audio": False,
            "export_data": True,
            "read_audit_logs": True,
            "manage_users": True,
            "access_anonymized_data": True,
        },
        "developer": {
            "read_own_data": False,
            "write_own_data": False,
            "read_patient_data": False,  # No access to identifiable data
            "write_patient_data": False,
            "read_raw_audio": False,  # No access to raw recordings
            "write_raw_audio": False,
            "export_data": False,
            "read_audit_logs": False,
            "manage_users": False,
            "access_anonymized_data": True,  # Only anonymized data
        },
        "auditor": {
            "read_own_data": False,
            "write_own_data": False,
            "read_patient_data": False,
            "write_patient_data": False,
            "read_raw_audio": False,
            "write_raw_audio": False,
            "export_data": False,
            "read_audit_logs": True,  # Primary purpose
            "manage_users": False,
            "access_anonymized_data": True,  # For compliance reporting
        },
    }

    # Session timeout (30 minutes)
    SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

    @staticmethod
    def get_user_roles(user_id: int, db) -> List[str]:
        """Get all active roles for a user"""
        from security_models import UserRoleAssignment

        roles = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.is_active == True
        ).all()

        return [role.role.value for role in roles]

    @staticmethod
    def has_permission(user_id: int, permission: str, db) -> bool:
        """Check if user has a specific permission"""
        roles = RBACManager.get_user_roles(user_id, db)

        for role in roles:
            role_perms = RBACManager.ROLE_PERMISSIONS.get(role, {})
            if role_perms.get(permission, False):
                return True

        return False

    @staticmethod
    def assign_role(user_id: int, role: str, assigned_by: int, clinic_id: Optional[str], db):
        """Assign a role to a user"""
        from security_models import UserRoleAssignment, UserRole

        # Validate role
        try:
            role_enum = UserRole(role)
        except ValueError:
            raise ValueError(f"Invalid role: {role}")

        # Check if assignment already exists
        existing = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role == role_enum,
            UserRoleAssignment.is_active == True,
            UserRoleAssignment.clinic_id == clinic_id
        ).first()

        if existing:
            return existing

        # Create new assignment
        assignment = UserRoleAssignment(
            user_id=user_id,
            role=role_enum,
            assigned_by=assigned_by,
            clinic_id=clinic_id,
            is_active=True
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        return assignment

    @staticmethod
    def check_session_timeout(session, current_time: datetime) -> bool:
        """Check if session has timed out (30 minutes idle)"""
        timeout = timedelta(minutes=RBACManager.SESSION_TIMEOUT_MINUTES)
        time_since_activity = current_time - session.last_activity

        return time_since_activity > timeout

    @staticmethod
    def update_session_activity(session, db):
        """Update last activity timestamp for session"""
        session.last_activity = datetime.utcnow()
        db.add(session)
        db.commit()


def require_permission(permission: str):
    """
    Decorator to require a specific permission for a route.

    Usage:
        @app.get("/patient/{id}")
        @require_permission("read_patient_data")
        def get_patient(id: int, user = Depends(get_current_user), db = Depends(get_db)):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user and db from kwargs
            user = kwargs.get('user')
            db = kwargs.get('db')

            if not user or not db:
                raise PermissionDenied("Authentication required")

            # Check permission
            if not RBACManager.has_permission(user.id, permission, db):
                raise PermissionDenied(f"User does not have permission: {permission}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role: str):
    """
    Decorator to require a specific role for a route.

    Usage:
        @app.get("/admin/users")
        @require_role("admin")
        def list_users(user = Depends(get_current_user), db = Depends(get_db)):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            db = kwargs.get('db')

            if not user or not db:
                raise PermissionDenied("Authentication required")

            roles = RBACManager.get_user_roles(user.id, db)
            if role not in roles:
                raise PermissionDenied(f"User does not have required role: {role}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Middleware for session timeout enforcement
class SessionTimeoutMiddleware:
    """
    Middleware to enforce automatic session timeout after 30 minutes of inactivity.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            # Check if user has active session
            token = request.cookies.get("access_token")
            if token:
                # This would need integration with session tracking
                # For now, this is a placeholder for the logic
                pass

        await self.app(scope, receive, send)
