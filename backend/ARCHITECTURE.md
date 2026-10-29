# DermaTrack Backend Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                          │
│                          (main.py)                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   CORS       │  │ Rate Limit   │  │    Static Files          │  │
│  │ Middleware   │  │  Middleware  │  │    (Media Mounting)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                          Route Layer                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │   Auth     │  │  Patients  │  │   Notes    │  │Consultations  │ │
│  │ /auth/*    │  │ /patients* │  │  /notes/*  │  │  /consult*    │ │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘   │
│                                                                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │  Consent   │  │     AI     │  │   Media    │  │   Health   │   │
│  │/consent-log│  │  /suggest* │  │ /transcribe│  │   /health  │   │
│  │            │  │ /soap_auto │  │            │  │            │   │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘   │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                      Dependency Layer                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │  get_db()       │    │ get_current_user│    │   Config Vars   │ │
│  │  (Session)      │    │  (User Auth)    │    │                 │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                   Business Logic Layer                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  auth.py     │  │  utils.py    │  │    schemas.py            │  │
│  │              │  │              │  │  (Validation)            │  │
│  │ • Password   │  │ • Sanitize   │  │                          │  │
│  │ • JWT tokens │  │ • Suggestions│  │ • Request models         │  │
│  │ • Validation │  │ • Type conv. │  │ • Response models        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                      Data Access Layer                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ database.py  │  │  models.py   │  │     config.py            │  │
│  │              │  │              │  │                          │  │
│  │ • Engine     │  │ • User       │  │ • Database URL           │  │
│  │ • Pool       │  │ • Patient    │  │ • API keys               │  │
│  │ • Session    │  │ • Note       │  │ • CORS settings          │  │
│  │ • Migrations │  │ • Consult    │  │ • Auth settings          │  │
│  │              │  │ • Consent    │  │ • Validation             │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                      Storage Layer                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────┐          ┌──────────────────────────────┐  │
│  │   SQLite/PostgreSQL │          │  Local Filesystem (Media)    │  │
│  │     Database        │          │  or S3 (Optional)            │  │
│  └─────────────────────┘          └──────────────────────────────┘  │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                    External Services                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Google Gemini│  │ Faster-Whisper│ │  OpenAI Whisper (alt)   │  │
│  │ (SOAP notes) │  │  (Local)      │  │  (Alternative backend) │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │           AWS S3 (Optional Audio Storage)                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Request Flow Example: Creating a Consultation

```
Client Request
    │
    ├─→ POST /consultations
    │
    ▼
┌─────────────────────────────┐
│  FastAPI Router             │
│  (consultations.py)         │
└─────────────────────────────┘
    │
    ├─→ Dependencies
    │   ├─→ get_current_user  (auth.py)
    │   ├─→ get_db           (database.py)
    │   └─→ Request          (FastAPI)
    │
    ├─→ Input Validation
    │   └─→ ConsultationIn   (schemas.py)
    │
    ▼
┌─────────────────────────────┐
│  Route Handler              │
│  create_consultation()      │
│                             │
│  1. Sanitize input (utils)  │
│  2. Resolve/create patient  │
│  3. Create consultation     │
│  4. Create consent record   │
│  5. Log audit trail         │
│  6. Commit to database      │
└─────────────────────────────┘
    │
    ├─→ Database Access
    │   └─→ SQLAlchemy Models (models.py)
    │
    ▼
┌─────────────────────────────┐
│  Database Layer             │
│  (SQLite/PostgreSQL)        │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  Response                   │
│  ConsultationOut (schemas)  │
└─────────────────────────────┘
    │
    ▼
Client Response (JSON)
```

## Module Dependencies

```
main.py
├── config
│   └── (reads .env)
│
├── database
│   ├── config
│   └── models
│
├── models
│
├── auth
│   ├── config
│   ├── database
│   └── models
│
├── schemas
│   └── (pydantic)
│
├── utils
│   └── (bleach)
│
└── routes/
    ├── auth.py
    │   ├── auth
    │   ├── schemas
    │   ├── database
    │   ├── models
    │   └── config
    │
    ├── patients.py
    │   ├── schemas
    │   ├── auth (dependency)
    │   ├── database
    │   ├── models
    │   └── utils
    │
    ├── notes.py
    │   ├── schemas
    │   ├── auth (dependency)
    │   ├── database
    │   ├── models
    │   └── utils
    │
    ├── consultations.py
    │   ├── schemas
    │   ├── auth (dependency)
    │   ├── database
    │   ├── models
    │   └── utils
    │
    ├── consent.py
    │   ├── schemas
    │   ├── auth (dependency)
    │   └── database
    │
    ├── ai.py
    │   ├── schemas
    │   ├── auth (dependency)
    │   ├── utils
    │   ├── config
    │   └── (genai API)
    │
    └── media.py
        ├── config
        ├── (boto3 for S3)
        └── (faster-whisper or openai)
```

## Data Flow: Authentication

```
┌────────────────────┐
│ User submits       │
│ credentials        │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐      ┌──────────────────┐
│ /auth/login        │─────→│ Validate Input   │
│ (routes/auth.py)   │      │ (schemas)        │
└────────────────────┘      └──────────────────┘
         │
         ▼
┌────────────────────┐      ┌──────────────────┐
│ Query Database     │─────→│ Find User        │
│ (models.User)      │      │ (database)       │
└────────────────────┘      └──────────────────┘
         │
         ▼
┌────────────────────┐      ┌──────────────────┐
│ Verify Password    │─────→│ Hash comparison  │
│ (auth.py)          │      │ (bcrypt)         │
└────────────────────┘      └──────────────────┘
         │
         ▼
┌────────────────────┐      ┌──────────────────┐
│ Create JWT         │─────→│ Token with exp   │
│ (auth.py)          │      │ date             │
└────────────────────┘      └──────────────────┘
         │
         ▼
┌────────────────────┐      ┌──────────────────┐
│ Set Secure Cookie  │─────→│ HttpOnly flag    │
│ (route handler)    │      │ CSRF protection  │
└────────────────────┘      └──────────────────┘
         │
         ▼
┌────────────────────┐
│ Return User Info   │
│ (schemas.UserOut)  │
└────────────────────┘
```

## Scaling Considerations

### Horizontal Scaling
- **Stateless**: All routes are stateless, can run on multiple servers
- **Connection pooling**: Database connections are pooled efficiently
- **Session management**: JWT tokens in cookies, no server-side sessions

### Vertical Scaling
- **Async support**: Transcription endpoint is async-ready
- **Database indexes**: Created on frequently queried fields
- **Query optimization**: Uses joinedload to prevent N+1 queries

### Future Improvements
- **Cache layer**: Redis for sessions, frequently accessed data
- **Background jobs**: Celery for async processing
- **Message queue**: Event streaming for real-time updates
- **CDN**: For media content delivery (S3 compatible)
- **Service mesh**: For multi-service architecture

## Security Layers

```
┌──────────────────────────────────────────┐
│  1. Network Layer                        │
│     • CORS validation                    │
│     • HTTPS enforced (secure cookies)    │
└──────────────────────────────────────────┘
         ▼
┌──────────────────────────────────────────┐
│  2. Authentication Layer                 │
│     • JWT token validation               │
│     • Password strength requirements     │
│     • Bcrypt hashing                     │
└──────────────────────────────────────────┘
         ▼
┌──────────────────────────────────────────┐
│  3. Authorization Layer                  │
│     • User ownership verification        │
│     • Resource-level access checks       │
└──────────────────────────────────────────┘
         ▼
┌──────────────────────────────────────────┐
│  4. Input Validation Layer               │
│     • Pydantic schema validation         │
│     • HTML sanitization                  │
│     • File type validation               │
└──────────────────────────────────────────┘
         ▼
┌──────────────────────────────────────────┐
│  5. Rate Limiting Layer                  │
│     • Endpoint-specific limits           │
│     • DDoS protection                    │
└──────────────────────────────────────────┘
         ▼
┌──────────────────────────────────────────┐
│  6. Audit & Logging Layer                │
│     • Consent logging                    │
│     • Action tracking                    │
└──────────────────────────────────────────┘
```
