# Database Migration Guide: SQLite to PostgreSQL

This guide explains the migration from SQLite3 to PostgreSQL for the DermTrack application.

## Overview

DermTrack has been migrated from SQLite3 to PostgreSQL for better scalability, concurrent access handling, and production readiness.

## What Changed

- **Database Engine**: SQLite3 → PostgreSQL 15
- **Connection String**: Now using `DATABASE_URL` environment variable
- **Schema**: No changes - all tables remain the same
- **Dependencies**: Already includes `psycopg2-binary==2.9.9`

## Setup Options

### Option 1: Local Development with Docker PostgreSQL (Recommended)

1. **Start PostgreSQL container:**
   ```bash
   docker-compose -f docker-compose.local.yml up -d
   ```

2. **Verify PostgreSQL is running:**
   ```bash
   docker-compose -f docker-compose.local.yml ps
   ```

3. **Configure environment:**
   Your `backend/.env` file should have:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/dermatack
   ```

4. **Run backend locally:**
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

   The database tables will be created automatically on first startup.

### Option 2: Full Docker Compose Stack

Run everything in Docker (PostgreSQL, backend, frontend):

```bash
docker-compose up --build
```

The backend will automatically connect to PostgreSQL using the connection string configured in `docker-compose.yml`.

### Option 3: Local PostgreSQL Installation

If you have PostgreSQL installed locally:

1. **Create database:**
   ```bash
   psql -U postgres
   CREATE DATABASE dermatack;
   \q
   ```

2. **Update `backend/.env`:**
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/dermatack
   ```

3. **Run backend:**
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

## Database Credentials

**Default credentials** (for development):
- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `dermatack`
- **Port**: `5432`

⚠️ **Change these for production deployments!**

## Data Migration (If You Have Existing Data)

If you have existing data in SQLite (`backend/app.db`), you can migrate it:

### Manual Migration Steps

1. **Export data from SQLite:**
   ```bash
   cd backend
   python -c "
   import sqlite3
   import json

   conn = sqlite3.connect('app.db')
   conn.row_factory = sqlite3.Row
   cursor = conn.cursor()

   # Export users
   cursor.execute('SELECT * FROM users')
   users = [dict(row) for row in cursor.fetchall()]

   # Export patients
   cursor.execute('SELECT * FROM patients')
   patients = [dict(row) for row in cursor.fetchall()]

   # Export consultations
   cursor.execute('SELECT * FROM consultations')
   consultations = [dict(row) for row in cursor.fetchall()]

   # Export notes
   cursor.execute('SELECT * FROM notes')
   notes = [dict(row) for row in cursor.fetchall()]

   with open('export.json', 'w') as f:
       json.dump({
           'users': users,
           'patients': patients,
           'consultations': consultations,
           'notes': notes
       }, f, indent=2, default=str)

   print('Data exported to export.json')
   "
   ```

2. **Start PostgreSQL and backend:**
   ```bash
   docker-compose -f docker-compose.local.yml up -d
   cd backend
   uvicorn main:app --reload
   ```

3. **Import data to PostgreSQL:**
   Create a Python script to import the JSON data using SQLAlchemy ORM.

## Verification

### Check PostgreSQL Connection

```bash
# Using docker-compose.local.yml
docker exec -it dermatack-db-local psql -U postgres -d dermatack

# In psql:
\dt  # List tables
SELECT COUNT(*) FROM users;
\q
```

### Check Backend Logs

The backend will log the database connection on startup:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/

# Register a test user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

## Troubleshooting

### Connection Refused

```
could not connect to server: Connection refused
```

**Solution**: Ensure PostgreSQL is running:
```bash
docker-compose -f docker-compose.local.yml ps
docker-compose -f docker-compose.local.yml logs db
```

### Database Does Not Exist

```
FATAL: database "dermatack" does not exist
```

**Solution**: The database should be created automatically by the container. If not:
```bash
docker exec -it dermatack-db-local psql -U postgres -c "CREATE DATABASE dermatack;"
```

### Port Already in Use

```
Bind for 0.0.0.0:5432 failed: port is already allocated
```

**Solution**: Another PostgreSQL instance is running. Either:
- Stop the other PostgreSQL: `sudo systemctl stop postgresql`
- Or change the port in `docker-compose.local.yml` to `5433:5432`

### Tables Not Created

The backend automatically creates tables on startup using SQLAlchemy's `Base.metadata.create_all()`. If tables are missing:

1. Check backend logs for errors
2. Verify `DATABASE_URL` is correct
3. Restart the backend

## Stopping PostgreSQL

```bash
# Stop without removing data
docker-compose -f docker-compose.local.yml stop

# Stop and remove containers (data persists in volume)
docker-compose -f docker-compose.local.yml down

# Remove everything including data
docker-compose -f docker-compose.local.yml down -v
```

## Environment Variables Reference

| Variable | Example | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/dermatack` | PostgreSQL connection string |
| `POSTGRES_USER` | `postgres` | Database user (docker-compose only) |
| `POSTGRES_PASSWORD` | `postgres` | Database password (docker-compose only) |
| `POSTGRES_DB` | `dermatack` | Database name (docker-compose only) |

## Production Considerations

For production deployments:

1. **Use strong passwords**: Change default `postgres` password
2. **Use managed PostgreSQL**: Consider AWS RDS, Google Cloud SQL, etc.
3. **Enable SSL**: Use `?sslmode=require` in `DATABASE_URL`
4. **Connection pooling**: Configure SQLAlchemy pool size
5. **Backups**: Set up automated PostgreSQL backups
6. **Monitoring**: Monitor database performance and connections

## Rollback to SQLite (Not Recommended)

If you need to temporarily rollback to SQLite:

1. Comment out `DATABASE_URL` in `backend/.env`
2. The application will default to SQLite: `sqlite:///./app.db`
3. Restart the backend

Note: This will use the old SQLite database. Any data created in PostgreSQL won't be available.

## Support

If you encounter issues:
1. Check the logs: `docker-compose -f docker-compose.local.yml logs db`
2. Verify environment variables in `backend/.env`
3. Ensure the PostgreSQL container is healthy: `docker ps`
4. Review the connection string format carefully

## Database Schema

The application uses the following tables:

- **users**: User accounts
- **patients**: Patient records
- **consultations**: Audio consultations and transcripts
- **notes**: Clinical notes linked to consultations

All tables are automatically created by SQLAlchemy on first startup.
