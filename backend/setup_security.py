#!/usr/bin/env python3
"""
Security Infrastructure Setup Script for DermTrack

This script initializes the security infrastructure:
1. Creates database tables
2. Generates encryption key (if not exists)
3. Creates initial admin user
4. Sets up folder structure
5. Validates configuration

Usage:
    python setup_security.py [--skip-admin] [--force]

Options:
    --skip-admin    Skip admin user creation
    --force         Force recreate tables (WARNING: destroys data!)
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def setup_database(force=False):
    """Create security database tables"""
    print("\n" + "="*60)
    print("Step 1: Setting up database tables")
    print("="*60)

    from main import engine, Base
    from security_models import Base as SecurityBase

    if force:
        print("⚠️  WARNING: Force mode - dropping all tables!")
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() != 'yes':
            print("Aborted")
            sys.exit(1)

        Base.metadata.drop_all(bind=engine)
        SecurityBase.metadata.drop_all(bind=engine)
        print("✓ Existing tables dropped")

    # Create tables
    Base.metadata.create_all(bind=engine)
    print("✓ Main application tables created")

    SecurityBase.metadata.create_all(bind=engine)
    print("✓ Security tables created:")
    print("  - user_roles (RBAC)")
    print("  - consent_records")
    print("  - audit_logs")
    print("  - data_lifecycle")
    print("  - encryption_keys")
    print("  - user_sessions")


def setup_folders():
    """Create data storage folder structure"""
    print("\n" + "="*60)
    print("Step 2: Creating folder structure")
    print("="*60)

    folders = [
        "data_storage/raw_data",
        "data_storage/processed_data",
        "data_storage/metadata",
        "data_storage/audit_logs",
    ]

    for folder in folders:
        path = Path(folder)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {folder}")

    # Create .gitkeep files to preserve folder structure
    for folder in folders:
        gitkeep = Path(folder) / ".gitkeep"
        gitkeep.touch()


def check_encryption_key():
    """Check if encryption key is configured"""
    print("\n" + "="*60)
    print("Step 3: Checking encryption key")
    print("="*60)

    key = os.getenv("ENCRYPTION_KEY")

    if not key:
        print("⚠️  WARNING: No encryption key found in environment!")
        print("\nGenerating new encryption key...")

        from security.encryption import EncryptionManager
        new_key = EncryptionManager.generate_key()

        print(f"\n{'='*60}")
        print("NEW ENCRYPTION KEY GENERATED")
        print(f"{'='*60}")
        print(f"\nEncryption Key: {new_key}")
        print(f"\n⚠️  IMPORTANT: Add this to your .env file:")
        print(f"\nENCRYPTION_KEY={new_key}")
        print(f"\n{'='*60}")

        # Try to append to .env
        env_file = Path(".env")
        if env_file.exists():
            response = input("\nAppend to .env file? (y/n): ")
            if response.lower() == 'y':
                with open(env_file, 'a') as f:
                    f.write(f"\n# Generated encryption key - {datetime.utcnow().isoformat()}\n")
                    f.write(f"ENCRYPTION_KEY={new_key}\n")
                print("✓ Key appended to .env file")
        else:
            print("⚠️  .env file not found. Please create it manually.")

    else:
        print(f"✓ Encryption key found (length: {len(key)} chars)")

        # Validate key
        try:
            import base64
            decoded = base64.b64decode(key)
            if len(decoded) == 32:
                print(f"✓ Key is valid (256 bits)")
            else:
                print(f"⚠️  WARNING: Key is {len(decoded)*8} bits, expected 256 bits")
        except Exception as e:
            print(f"⚠️  WARNING: Key validation failed: {e}")


def create_admin_user(skip=False):
    """Create initial admin user"""
    if skip:
        print("\n" + "="*60)
        print("Step 4: Skipping admin user creation")
        print("="*60)
        return

    print("\n" + "="*60)
    print("Step 4: Creating admin user")
    print("="*60)

    from main import SessionLocal, User, hash_password
    from security.rbac import RBACManager

    db = SessionLocal()

    # Check if admin already exists
    admin = db.query(User).filter(User.email == "admin@dermtrack.local").first()

    if admin:
        print("⚠️  Admin user already exists")
        print(f"   Email: {admin.email}")
        print(f"   ID: {admin.id}")

        # Check if has admin role
        roles = RBACManager.get_user_roles(admin.id, db)
        if "admin" in roles:
            print(f"   Roles: {', '.join(roles)}")
        else:
            print(f"   Current roles: {', '.join(roles)}")
            print("   Adding admin role...")
            RBACManager.assign_role(
                user_id=admin.id,
                role="admin",
                assigned_by=None,
                clinic_id="default",
                db=db
            )
            print("✓ Admin role assigned")

        db.close()
        return

    # Create new admin user
    print("\nCreating new admin user...")
    print("Email: admin@dermtrack.local")

    default_password = "DermTrack2025!"  # Change immediately after first login

    admin = User(
        email="admin@dermtrack.local",
        password_hash=hash_password(default_password)
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    print(f"✓ Admin user created (ID: {admin.id})")

    # Assign admin role
    RBACManager.assign_role(
        user_id=admin.id,
        role="admin",
        assigned_by=None,
        clinic_id="default",
        db=db
    )

    print("✓ Admin role assigned")

    print(f"\n{'='*60}")
    print("ADMIN CREDENTIALS")
    print(f"{'='*60}")
    print(f"Email:    admin@dermtrack.local")
    print(f"Password: {default_password}")
    print(f"\n⚠️  CHANGE THIS PASSWORD IMMEDIATELY AFTER FIRST LOGIN!")
    print(f"{'='*60}")

    db.close()


def validate_setup():
    """Validate that everything is set up correctly"""
    print("\n" + "="*60)
    print("Step 5: Validating setup")
    print("="*60)

    errors = []
    warnings = []

    # Check database connection
    try:
        from main import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        print("✓ Database connection OK")
    except Exception as e:
        errors.append(f"Database connection failed: {e}")

    # Check tables exist
    try:
        from main import engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        required_tables = [
            "users", "patients", "consultations", "notes",
            "user_roles", "consent_records", "audit_logs",
            "data_lifecycle", "encryption_keys", "user_sessions"
        ]

        missing = [t for t in required_tables if t not in tables]
        if missing:
            errors.append(f"Missing tables: {', '.join(missing)}")
        else:
            print(f"✓ All required tables exist ({len(required_tables)} tables)")
    except Exception as e:
        errors.append(f"Table check failed: {e}")

    # Check folders exist
    folders = [
        "data_storage/raw_data",
        "data_storage/processed_data",
        "data_storage/metadata",
        "data_storage/audit_logs",
    ]

    missing_folders = [f for f in folders if not Path(f).exists()]
    if missing_folders:
        warnings.append(f"Missing folders: {', '.join(missing_folders)}")
    else:
        print(f"✓ All data storage folders exist")

    # Check encryption key
    if not os.getenv("ENCRYPTION_KEY"):
        warnings.append("ENCRYPTION_KEY not set in environment")
    else:
        print("✓ Encryption key configured")

    # Check cron script exists
    if not Path("cron_jobs/auto_delete.py").exists():
        warnings.append("Automated deletion script not found")
    else:
        print("✓ Automated deletion script exists")

    # Report results
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)

    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")

    if not errors and not warnings:
        print("\n✓ All checks passed!")

    print("\n" + "="*60)

    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(description="DermTrack Security Infrastructure Setup")
    parser.add_argument(
        "--skip-admin",
        action="store_true",
        help="Skip admin user creation"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreate tables (WARNING: destroys existing data!)"
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("DermTrack Security Infrastructure Setup")
    print("="*60)
    print(f"Started at: {datetime.utcnow().isoformat()}Z")

    try:
        # Run setup steps
        setup_database(force=args.force)
        setup_folders()
        check_encryption_key()
        create_admin_user(skip=args.skip_admin)
        success = validate_setup()

        # Final message
        print("\n" + "="*60)
        if success:
            print("✓ Setup completed successfully!")
            print("\nNext steps:")
            print("1. Review and update .env file with encryption key")
            print("2. Change admin password on first login")
            print("3. Set up automated deletion cron job:")
            print("   crontab -e")
            print("   0 * * * * cd /path/to/DermTrack/backend && python cron_jobs/auto_delete.py")
            print("4. Review legal templates:")
            print("   - legal_templates/PRIVACY_POLICY.md")
            print("   - legal_templates/DATA_PROCESSING_AGREEMENT.md")
            print("5. See INTEGRATION_GUIDE.md for code integration")
            print("="*60)
            return 0
        else:
            print("⚠️  Setup completed with errors. Please review above.")
            print("="*60)
            return 1

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
