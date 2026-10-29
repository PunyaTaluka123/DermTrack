# Troubleshooting Guide

## Common Issues and Solutions

### 1. "Could not import module main_new" Error

**Problem**: When starting the application, you see:
```
ERROR:    Error loading ASGI app. Could not import module "main_new".
```

**Solution**: Clear Python cache files and restart
```bash
cd backend
rm -rf __pycache__ .pytest_cache
find . -type d -name __pycache__ -exec rm -rf {} +
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Why**: Python caches compiled bytecode. If the old filename is in the cache, it can cause import errors.

---

### 2. "ModuleNotFoundError: No module named 'config'"

**Problem**:
```
ModuleNotFoundError: No module named 'config'
```

**Solution**: Ensure you're running from the `backend` directory
```bash
cd backend
python -m uvicorn main:app
```

**Why**: The modular files are relative imports. They must be imported from the correct directory.

---

### 3. "No such file or directory: 'media/audio'"

**Problem**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'media/audio'
```

**Solution**: Create the media directories
```bash
cd backend
mkdir -p media/audio
```

**Why**: The application mounts a static file directory. It must exist before startup.

---

### 4. "GEMINI_API_KEY not configured" Warning

**Problem**:
```
WARNING: GEMINI_API_KEY not set - SOAP notes feature will not work
```

**Solution**: Add to your `.env` file
```
GEMINI_API_KEY=your_api_key_here
```

**Why**: The SOAP notes feature requires a Gemini API key. It's optional, but without it, the `/soap_autofill` endpoint will fail.

---

### 5. "SECRET_KEY must be changed in production"

**Problem**:
```
RuntimeError: Configuration errors:
- SECRET_KEY must be changed in production
```

**Solution**: Update your `.env` file in production
```
ENVIRONMENT=production
SECRET_KEY=your_very_long_random_secret_key_with_32_characters_minimum
```

**Why**: Development secret keys are intentionally weak for easy setup. Production requires strong, unique keys.

---

### 6. Database Connection Errors

**Problem**:
```
sqlalchemy.exc.OperationalError: unable to open database file
```

**Solution**: Check your DATABASE_URL in `.env`
```bash
# For SQLite (default)
DATABASE_URL=sqlite:///./app.db

# For PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/dbname
```

**Why**: The database connection string may be incorrect or the database server may be down.

---

### 7. "Whisper model not loaded" Error

**Problem**:
```
HTTPException: status_code=503, detail="Whisper model not loaded"
```

**Solution**: Either set up local Whisper or use OpenAI API
```bash
# Option 1: Use local Whisper
# Install dependencies
pip install faster-whisper

# In .env
TRANSCRIBE_BACKEND=local

# Option 2: Use OpenAI API
pip install openai

# In .env
TRANSCRIBE_BACKEND=openai
OPENAI_API_KEY=your_key_here
```

**Why**: The transcription endpoint requires either a Whisper model or OpenAI API key.

---

### 8. "Port 8000 already in use"

**Problem**:
```
OSError: [Errno 48] Address already in use
```

**Solution**: Either use a different port or kill the existing process
```bash
# Use a different port
python -m uvicorn main:app --port 8001

# Or kill the process using port 8000
lsof -ti :8000 | xargs kill -9
```

**Why**: Another application is already using port 8000.

---

### 9. CORS Errors in Frontend

**Problem**:
```
Access to XMLHttpRequest at 'http://localhost:8000/...' from origin 'http://localhost:3000'
has been blocked by CORS policy
```

**Solution**: Update CORS settings in `.env`
```
FRONTEND_ORIGIN=http://localhost:3000
# For multiple origins, use comma-separated
FRONTEND_ORIGIN=http://localhost:3000,http://localhost:3001
```

**Why**: CORS must be configured to allow requests from your frontend.

---

### 10. "Pydantic validation error"

**Problem**:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error
```

**Solution**: Check your request payload matches the schema
```bash
# Example: Create patient
curl -X POST http://localhost:8000/patients \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=your_token" \
  -d '{"name": "John Doe"}'  # name is required
```

**Why**: The request data doesn't match the Pydantic schema requirements.

---

## Testing the Application

### Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"ok": true}
```

### Authentication Test
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123"
  }'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123"
  }'
```

### Check Endpoints
```bash
# Get current user
curl -b "access_token=YOUR_TOKEN" http://localhost:8000/auth/me

# List patients
curl -b "access_token=YOUR_TOKEN" http://localhost:8000/patients

# Create patient
curl -X POST -b "access_token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe"}' \
  http://localhost:8000/patients
```

---

## Debugging Tips

### 1. Enable SQL Logging
Add to `.env`:
```
DB_ECHO=true
```

This will print all SQL queries to the console.

### 2. Check Module Imports
```bash
cd backend
python -c "from routes import auth, patients, notes, consultations, consent, ai, media; print('All routes import OK')"
```

### 3. Verify Configuration
```bash
cd backend
python -c "from config import *; print('Config loaded successfully')"
```

### 4. Test Database Connection
```bash
cd backend
python -c "from database import engine; print(engine); engine.connect()"
```

### 5. Check Python Version
```bash
python --version
# Should be Python 3.8+ (preferably 3.10+)
```

---

## Performance Issues

### Application Running Slow

**Check**:
1. Database pool settings
   ```
   DB_POOL_SIZE=10
   DB_MAX_OVERFLOW=20
   ```

2. N+1 queries in logs (if DB_ECHO=true)
   - Look for repeated SELECT queries

3. Large files being processed
   - Check upload size limits (50MB max for audio)

4. System resources
   ```bash
   # Check CPU and memory
   top
   # or
   htop
   ```

---

## File Permission Issues

If you get permission errors:

```bash
cd backend
chmod -R 755 .
chmod -R 644 *.py
chmod 755 routes/*.py
```

---

## Upgrade Issues

### After Updating Dependencies

Clear cache and reinstall:
```bash
cd backend
rm -rf __pycache__ .pytest_cache
pip install --upgrade -r requirements.txt
```

---

## Getting Help

### Check Logs
1. Application output (console)
2. Database logs (if using PostgreSQL)
3. System logs (Windows Event Viewer / syslog)

### Check Documentation
- [MODULAR_STRUCTURE.md](./MODULAR_STRUCTURE.md) - Architecture
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [main_original.py](./main_original.py) - Original implementation

### Useful Commands

```bash
# Test import
python -c "from main import app"

# Run with debug output
python -m uvicorn main:app --log-level debug

# Check configuration
python -c "import config; print(dir(config))"

# Validate environment
python -c "from config import validate_config; validate_config()"
```

---

## If All Else Fails

### Rollback to Original
```bash
cd backend
mv main.py main_modular.py
mv main_original.py main.py
# Restart application
```

### Start Fresh
```bash
cd backend
rm -rf __pycache__ .pytest_cache app.db
# Delete only if safe!
```

### Reset Environment
```bash
# Create fresh .env from example
cp .env.example .env
# Edit .env with your settings
```

---

## Support Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Uvicorn Docs**: https://www.uvicorn.org/

---

Last Updated: 2024-11-02
