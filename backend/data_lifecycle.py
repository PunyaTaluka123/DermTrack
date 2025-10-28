"""
Data Lifecycle Management for DermTrack.
Implements automatic deletion, retention policies, and compliance tracking.

Retention Policies:
- Raw audio/video: Deleted within 24 hours
- Processed text: Kept 30 days max
- Anonymized training data: Kept 5 years max
- Consent logs and audit trails: Kept 7 years
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session
import hashlib
import os
import secrets


class DataRetentionPolicy:
    """Define retention policies for different data types"""

    # Retention periods (in days)
    RAW_AUDIO_VIDEO_DAYS = 1  # 24 hours
    PROCESSED_TEXT_DAYS = 30
    ANONYMIZED_DATA_DAYS = 365 * 5  # 5 years
    CONSENT_LOGS_DAYS = 365 * 7  # 7 years
    AUDIT_LOGS_DAYS = 365 * 7  # 7 years

    FILE_TYPE_RETENTION = {
        "raw_audio": RAW_AUDIO_VIDEO_DAYS,
        "raw_video": RAW_AUDIO_VIDEO_DAYS,
        "processed_text": PROCESSED_TEXT_DAYS,
        "processed_transcript": PROCESSED_TEXT_DAYS,
        "anonymized_data": ANONYMIZED_DATA_DAYS,
        "consent_record": CONSENT_LOGS_DAYS,
        "audit_log": AUDIT_LOGS_DAYS,
    }

    @classmethod
    def get_retention_period(cls, file_type: str) -> int:
        """Get retention period in days for a file type"""
        return cls.FILE_TYPE_RETENTION.get(file_type, cls.PROCESSED_TEXT_DAYS)

    @classmethod
    def calculate_deletion_date(cls, file_type: str, upload_date: datetime) -> datetime:
        """Calculate when a file should be deleted"""
        retention_days = cls.get_retention_period(file_type)
        return upload_date + timedelta(days=retention_days)


class LifecycleManager:
    """
    Manages the full lifecycle of sensitive medical data files.

    Lifecycle stages:
    1. Upload -> Calculate hash, store metadata, schedule deletion
    2. Process -> Update status, maintain hash integrity
    3. Return output -> Deliver results to user
    4. Auto-delete -> Remove file after retention period, log deletion with hash
    """

    def __init__(self, db: Session, base_storage_path: Path = Path("backend/data_storage")):
        self.db = db
        self.base_storage_path = base_storage_path

    def register_file(
        self,
        file_path: Path,
        file_type: str,
        user_id: int,
        consultation_id: Optional[int] = None,
        clinic_id: Optional[str] = None
    ) -> dict:
        """
        Register a new file in the lifecycle tracking system.

        Args:
            file_path: Path to the file
            file_type: Type of file (raw_audio, processed_text, etc.)
            user_id: ID of user who uploaded
            consultation_id: Associated consultation ID
            clinic_id: Clinic ID for multi-tenant setups

        Returns:
            Metadata dict with file_id, hash, scheduled_deletion
        """
        from security_models import DataLifecycleRecord
        from security.encryption import EncryptionManager

        # Calculate file hash for integrity
        file_hash = EncryptionManager.calculate_checksum(file_path)

        # Generate unique file ID
        file_id = f"{file_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(8)}"

        # Calculate deletion date based on retention policy
        upload_time = datetime.utcnow()
        deletion_date = DataRetentionPolicy.calculate_deletion_date(file_type, upload_time)

        # Create lifecycle record
        record = DataLifecycleRecord(
            file_id=file_id,
            file_type=file_type,
            file_path=str(file_path),
            file_hash=file_hash,
            uploaded_at=upload_time,
            scheduled_deletion=deletion_date,
            user_id=user_id,
            consultation_id=consultation_id,
            clinic_id=clinic_id,
            is_deleted=False,
            deletion_verified=False
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        return {
            "file_id": file_id,
            "file_hash": file_hash,
            "uploaded_at": upload_time.isoformat(),
            "scheduled_deletion": deletion_date.isoformat(),
            "retention_days": DataRetentionPolicy.get_retention_period(file_type)
        }

    def mark_processed(self, file_id: str):
        """Mark a file as processed"""
        from security_models import DataLifecycleRecord

        record = self.db.query(DataLifecycleRecord).filter(
            DataLifecycleRecord.file_id == file_id
        ).first()

        if record:
            record.processed_at = datetime.utcnow()
            self.db.commit()

    def delete_file(self, file_id: str, verify_hash: bool = True) -> dict:
        """
        Delete a file and log the deletion with timestamp and hash.

        Args:
            file_id: File ID from lifecycle record
            verify_hash: Whether to verify file hash before deletion

        Returns:
            Deletion metadata with hash and timestamp
        """
        from security_models import DataLifecycleRecord
        from security.audit import AuditLogger

        record = self.db.query(DataLifecycleRecord).filter(
            DataLifecycleRecord.file_id == file_id,
            DataLifecycleRecord.is_deleted == False
        ).first()

        if not record:
            raise ValueError(f"File not found or already deleted: {file_id}")

        file_path = Path(record.file_path)
        original_hash = record.file_hash

        # Verify hash before deletion if requested
        if verify_hash and file_path.exists():
            from security.encryption import EncryptionManager
            current_hash = EncryptionManager.calculate_checksum(file_path)

            if current_hash != original_hash:
                # File has been tampered with!
                AuditLogger.log(
                    db=self.db,
                    action="delete_failed",
                    resource_type=record.file_type,
                    user_id=None,  # System action
                    resource_id=file_id,
                    success=False,
                    error_message=f"Hash mismatch: expected {original_hash}, got {current_hash}"
                )
                raise ValueError(f"File integrity check failed for {file_id}")

        # Delete the file
        deleted_at = datetime.utcnow()
        if file_path.exists():
            file_path.unlink()

        # Update lifecycle record
        record.deleted_at = deleted_at
        record.is_deleted = True
        record.deletion_verified = not file_path.exists()

        self.db.commit()

        # Log deletion in audit trail
        AuditLogger.log_deletion(
            db=self.db,
            user_id=None,  # System-initiated deletion
            resource_type=record.file_type,
            resource_id=file_id,
            file_hash=original_hash,
            reason="scheduled_deletion"
        )

        return {
            "file_id": file_id,
            "file_hash": original_hash,
            "deleted_at": deleted_at.isoformat(),
            "verified": record.deletion_verified
        }

    def get_files_for_deletion(self, check_time: Optional[datetime] = None) -> List:
        """
        Get all files that are scheduled for deletion.

        Args:
            check_time: Time to check against (defaults to now)

        Returns:
            List of DataLifecycleRecord objects ready for deletion
        """
        from security_models import DataLifecycleRecord

        if check_time is None:
            check_time = datetime.utcnow()

        return self.db.query(DataLifecycleRecord).filter(
            DataLifecycleRecord.is_deleted == False,
            DataLifecycleRecord.scheduled_deletion <= check_time
        ).all()

    def run_scheduled_deletions(self) -> dict:
        """
        Run scheduled deletions for all files past their retention period.

        Returns:
            Summary of deletion results
        """
        files_to_delete = self.get_files_for_deletion()

        results = {
            "total": len(files_to_delete),
            "deleted": 0,
            "failed": 0,
            "errors": []
        }

        for record in files_to_delete:
            try:
                self.delete_file(record.file_id, verify_hash=True)
                results["deleted"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "file_id": record.file_id,
                    "error": str(e)
                })

        return results

    def get_file_status(self, file_id: str) -> Optional[dict]:
        """Get current status of a file in the lifecycle"""
        from security_models import DataLifecycleRecord

        record = self.db.query(DataLifecycleRecord).filter(
            DataLifecycleRecord.file_id == file_id
        ).first()

        if not record:
            return None

        return {
            "file_id": record.file_id,
            "file_type": record.file_type,
            "file_hash": record.file_hash,
            "uploaded_at": record.uploaded_at.isoformat(),
            "processed_at": record.processed_at.isoformat() if record.processed_at else None,
            "scheduled_deletion": record.scheduled_deletion.isoformat(),
            "deleted_at": record.deleted_at.isoformat() if record.deleted_at else None,
            "is_deleted": record.is_deleted,
            "deletion_verified": record.deletion_verified,
            "days_until_deletion": (record.scheduled_deletion - datetime.utcnow()).days if not record.is_deleted else 0
        }

    def cleanup_old_metadata(self, days: int = 30):
        """
        Clean up old lifecycle records (metadata only, not the files themselves).
        Keeps records for deleted files for audit purposes.

        Args:
            days: Keep metadata for deleted files for this many days
        """
        from security_models import DataLifecycleRecord

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Only delete metadata for files that were deleted long ago
        old_records = self.db.query(DataLifecycleRecord).filter(
            DataLifecycleRecord.is_deleted == True,
            DataLifecycleRecord.deleted_at < cutoff
        ).all()

        count = len(old_records)
        for record in old_records:
            self.db.delete(record)

        self.db.commit()

        return {"metadata_records_cleaned": count}
