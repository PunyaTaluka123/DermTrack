import os

from dotenv import load_dotenv

load_dotenv()

TRANSCRIBE_BACKEND = os.getenv("TRANSCRIBE_BACKEND", "local").lower()
RAW_FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
FRONTEND_ORIGINS = [origin.strip() for origin in RAW_FRONTEND_ORIGINS.split(",") if origin.strip()]
if not FRONTEND_ORIGINS:
    FRONTEND_ORIGINS = ["http://localhost:3000"]
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").lower() in ("1", "true", "yes")
SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN") or None
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax").lower()
if SESSION_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    SESSION_COOKIE_SAMESITE = "lax"


# Optional S3 audio storage
S3_ENABLED = os.getenv("S3_ENABLED", "false").lower() in ("1", "true", "yes")
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_REGION = os.getenv("AWS_REGION", os.getenv("S3_REGION", ""))
S3_PREFIX = os.getenv("S3_PREFIX", "dermatrack/audio/")
S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL", "")

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Global Whisper model instance (loaded at startup)
whisper_model = None

# Validate configuration at startup
def validate_config():
    """Validate required configuration and security settings"""
    errors = []

    # Check SECRET_KEY strength in production
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
    if not is_dev:
        if SECRET_KEY == "dev-secret-change-me":
            errors.append("SECRET_KEY must be changed in production")
        if len(SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 characters long")

    # Check required API keys
    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY not set - SOAP notes feature will not work")

    if errors:
        error_msg = "Configuration errors:\n" + "\n".join(f"- {e}" for e in errors)
        raise RuntimeError(error_msg)
