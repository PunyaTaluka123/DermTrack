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
