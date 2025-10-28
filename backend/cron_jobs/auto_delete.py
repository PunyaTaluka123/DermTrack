#!/usr/bin/env python3
"""
Automated deletion cron job for DermTrack.
Runs scheduled deletions with checksum verification and alert notifications.

Usage:
    python auto_delete.py [--dry-run] [--alert-email EMAIL]

Crontab example (runs every hour):
    0 * * * * cd /path/to/DermTrack/backend && python cron_jobs/auto_delete.py --alert-email admin@clinic.com
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import argparse
import json

# Add parent directory to path to import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data_lifecycle import LifecycleManager
from security.audit import AuditLogger


def send_alert_email(results: dict, recipient: str):
    """
    Send alert email with deletion results.

    In production, integrate with:
    - SendGrid
    - AWS SES
    - SMTP server
    - Slack webhook
    """
    subject = f"DermTrack Auto-Deletion Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"

    body = f"""
DermTrack Automated Deletion Report
====================================

Execution Time: {datetime.utcnow().isoformat()}Z

Summary:
--------
Total files checked: {results['total']}
Successfully deleted: {results['deleted']}
Failed deletions: {results['failed']}

"""

    if results['errors']:
        body += "\nErrors:\n-------\n"
        for error in results['errors']:
            body += f"- File ID: {error['file_id']}\n"
            body += f"  Error: {error['error']}\n\n"

    body += f"\nStatus: {'SUCCESS' if results['failed'] == 0 else 'PARTIAL FAILURE'}\n"

    # For now, just print (replace with actual email sending in production)
    print(f"\n{'=' * 60}")
    print(f"ALERT EMAIL TO: {recipient}")
    print(f"SUBJECT: {subject}")
    print(f"{'=' * 60}")
    print(body)
    print(f"{'=' * 60}\n")

    # TODO: Integrate with email service
    # Example:
    # import smtplib
    # from email.mime.text import MIMEText
    # msg = MIMEText(body)
    # msg['Subject'] = subject
    # msg['From'] = 'noreply@dermtrack.com'
    # msg['To'] = recipient
    # s = smtplib.SMTP('localhost')
    # s.send_message(msg)
    # s.quit()


def run_auto_deletion(dry_run: bool = False, alert_email: str = None):
    """
    Run the automated deletion process.

    Args:
        dry_run: If True, don't actually delete files, just report what would be deleted
        alert_email: Email address to send completion alert
    """
    print(f"\n{'=' * 60}")
    print(f"DermTrack Auto-Deletion Job")
    print(f"Started at: {datetime.utcnow().isoformat()}Z")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'=' * 60}\n")

    # Load database configuration
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/dermatack")

    # Create database connection
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()

    try:
        # Initialize lifecycle manager
        manager = LifecycleManager(db)

        if dry_run:
            # Dry run: just list files that would be deleted
            files_to_delete = manager.get_files_for_deletion()

            print(f"Found {len(files_to_delete)} files scheduled for deletion:\n")

            for record in files_to_delete:
                status = manager.get_file_status(record.file_id)
                print(f"  - File ID: {record.file_id}")
                print(f"    Type: {record.file_type}")
                print(f"    Hash: {record.file_hash[:16]}...")
                print(f"    Uploaded: {record.uploaded_at.isoformat()}")
                print(f"    Scheduled deletion: {record.scheduled_deletion.isoformat()}")
                print(f"    Days overdue: {abs(status['days_until_deletion'])}")
                print()

            results = {
                "total": len(files_to_delete),
                "deleted": 0,
                "failed": 0,
                "errors": []
            }

        else:
            # Live run: actually delete files
            print("Running scheduled deletions...\n")
            results = manager.run_scheduled_deletions()

            print(f"Deletion Results:")
            print(f"  Total: {results['total']}")
            print(f"  Deleted: {results['deleted']}")
            print(f"  Failed: {results['failed']}")

            if results['errors']:
                print(f"\nErrors encountered:")
                for error in results['errors']:
                    print(f"  - {error['file_id']}: {error['error']}")

        # Log cron job execution in audit trail
        AuditLogger.log(
            db=db,
            action="cron_auto_delete",
            resource_type="system",
            user_id=None,
            success=results['failed'] == 0,
            error_message=None if results['failed'] == 0 else f"{results['failed']} deletions failed",
            metadata={
                "total": results['total'],
                "deleted": results['deleted'],
                "failed": results['failed'],
                "dry_run": dry_run
            }
        )

        # Send alert email if configured
        if alert_email and not dry_run:
            send_alert_email(results, alert_email)

        print(f"\n{'=' * 60}")
        print(f"Completed at: {datetime.utcnow().isoformat()}Z")
        print(f"Status: {'SUCCESS' if results['failed'] == 0 else 'PARTIAL FAILURE'}")
        print(f"{'=' * 60}\n")

        # Return exit code
        return 0 if results['failed'] == 0 else 1

    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        # Log fatal error
        AuditLogger.log(
            db=db,
            action="cron_auto_delete",
            resource_type="system",
            user_id=None,
            success=False,
            error_message=str(e)
        )

        if alert_email:
            send_alert_email({
                "total": 0,
                "deleted": 0,
                "failed": 1,
                "errors": [{"file_id": "N/A", "error": str(e)}]
            }, alert_email)

        return 2

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="DermTrack Automated Deletion Cron Job")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - don't actually delete files, just report what would be deleted"
    )
    parser.add_argument(
        "--alert-email",
        type=str,
        help="Email address to send completion alert"
    )

    args = parser.parse_args()

    exit_code = run_auto_deletion(
        dry_run=args.dry_run,
        alert_email=args.alert_email
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
