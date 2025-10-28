# DermTrack Deployment Guide

DermTrack is a full-stack teledermatology toolkit composed of a FastAPI backend and a Next.js frontend. The project now ships with production-ready Docker images, a Postgres datastore for multi-device sync, and documented environment configuration.

## Stack Overview

- **Backend**: FastAPI, SQLAlchemy, JWT cookies, optional S3 audio storage
- **Frontend**: Next.js 15, Tailwind, client-side transcription UX
- **Database**: Postgres (via SQLAlchemy + psycopg2)
- **Transcription**: faster-whisper (local) or OpenAI Whisper (remote)
- **Containerisation**: Docker + docker-compose (backend, frontend, db)

## Prerequisites

- Docker Desktop >= 4.0 (includes docker-compose v2)
- Node.js 20+ and Python 3.11+ (for local development without Docker)
- An `.env` file for both backend and frontend (see samples below)

## Environment Configuration

Copy the sample files and adjust for your environment:

```bash
cp backend/.env.example backend/.env
cp derma-frontend/.env.example derma-frontend/.env
```

Key backend variables:

| Variable | Description |
| --- | --- |
| `FRONTEND_ORIGIN` | Comma-separated list of allowed frontend origins. Example: `https://app.example.com,https://admin.example.com`. |
| `SECRET_KEY` | JWT signing secret. Generate a long random string for production. |
| `SECURE_COOKIES` | Set to `true` in production (HTTPS required). |
| `SESSION_COOKIE_DOMAIN` | Optional cookie domain (e.g. `.example.com`). Leave blank for same-host deployments. |
| `SESSION_COOKIE_SAMESITE` | `lax`, `strict`, or `none`. Use `none` when serving frontend and backend on different domains (requires HTTPS + `SECURE_COOKIES=true`). |
| `DATABASE_URL` | Postgres URI, e.g. `postgresql+psycopg2://postgres:postgres@db:5432/dermatack`. |
| `TRANSCRIBE_BACKEND` | `local` (faster-whisper) or `openai`. |
| `S3_ENABLED` & `S3_*` | Toggle and configure S3 audio uploads (optional). |

Frontend only needs `NEXT_PUBLIC_API_BASE_URL`, pointing to the backend base URL. During Docker builds this is supplied automatically.

## Running with Docker (Recommended)

```bash
docker compose up --build
```

This command starts three containers:

| Service | Port | Notes |
| --- | --- | --- |
| `frontend` | `3000` | Next.js production server (`next start`). |
| `backend` | `8000` | FastAPI served by Uvicorn. Persists audio files under the `media` volume. |
| `db` | internal | Postgres 15; data persisted to the `db-data` volume. |

The frontend and backend communicate over the internal Docker network; user traffic enters via `http://localhost:3000`.

### Persisted Volumes

- `db-data`: Retains your Postgres data between restarts (multi-device sync).
- `media`: Stores uploaded audio artifacts. Map this to durable storage in production if you opt out of S3.

### Production Hardening

Before promoting to production:

1. Configure HTTPS (reverse proxy or cloud load balancer).
2. Set `SECURE_COOKIES=true` and `SESSION_COOKIE_SAMESITE=none` when serving frontend and backend on different domains; also set `SESSION_COOKIE_DOMAIN` if using wildcard domains.
3. Replace the default `SECRET_KEY` with a securely generated value.
4. Update `FRONTEND_ORIGIN` to your public frontend URL(s).
5. Point `NEXT_PUBLIC_API_BASE_URL` to the public backend URL (e.g., `https://api.example.com`).
6. For auto-scaling, ensure the Postgres connection string references managed storage (e.g., RDS, Cloud SQL).

## Local Development (Without Docker)

1. **Backend**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Frontend**
   ```bash
   cd derma-frontend
   npm install
   npm run dev
   ```

## Deployment Workflow

1. Build container images (CI/CD) using the provided Dockerfiles. Example tags:
   ```bash
   docker build -f Dockerfile.backend -t registry.example.com/dermatrack-backend:latest .
   docker build -f Dockerfile.frontend -t registry.example.com/dermatrack-frontend:latest .
   ```

2. Push images to your container registry.
3. Provision managed Postgres and set `DATABASE_URL` accordingly.
4. Deploy to your platform of choice (ECS, GKE, Kubernetes, Azure, etc.). Ensure the frontend service can reach the backend service URL specified by `NEXT_PUBLIC_API_BASE_URL`.
5. Configure HTTPS termination and forward `X-Forwarded-*` headers if using a reverse proxy/load balancer.

## Multi-Device Data Sync

All patient, consultation, and note data persist in Postgres, allowing doctors to access the same workspace across devices. Audio artifacts are retained either inside the Docker volume (`media`) or in S3 when `S3_ENABLED=true`.

## Optional S3 Audio Storage

Set the following environment variables when you want audio files uploaded to S3 instead of the local `media` directory:

```env
S3_ENABLED=true
S3_BUCKET=your-audio-bucket
AWS_REGION=us-east-1
S3_PUBLIC_URL=https://your-cdn.example.com  # optional CDN/domain
```

The backend will fall back to local storage if S3 uploads fail.

## Health Checks

- Backend: `GET /health`
- Docker Compose Postgres health check ensures the API waits for a ready database.

## Troubleshooting

- **Cookie authentication fails cross-domain**: Set `SECURE_COOKIES=true`, `SESSION_COOKIE_SAMESITE=none`, and supply `SESSION_COOKIE_DOMAIN`.
- **Audio transcription errors**: Verify faster-whisper model availability, GPU drivers (if using), or configure `TRANSCRIBE_BACKEND=openai` with `OPENAI_API_KEY`.
- **Database connection issues**: Ensure `DATABASE_URL` uses the correct driver prefix (`postgresql+psycopg2://`).

With these changes you can deploy DermTrack to production, scale across multiple devices, and retain patient data in a central Postgres instance.

