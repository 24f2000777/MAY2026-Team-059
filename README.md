<div align="center">

# 🏛️ NAGRIK AI

### AI-Powered Civic Complaint Management Platform

> An intelligent civic grievance management platform that leverages Artificial Intelligence, Retrieval-Augmented Generation (RAG), asynchronous task processing, and modern backend engineering practices to streamline complaint registration, tracking, prioritization, and resolution.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://sqlalchemy.org)

**Team 059** • IIT Madras • Software Engineering • 2026

---

*A scalable backend for intelligent civic complaint management.*

</div>

---

# 📖 Table of Contents

- Overview
- Features
- Technology Stack
- High-Level Architecture
- Authentication — Complete Reference
- Standard API Response Format
- Folder Structure
- Getting Started
- Environment Configuration
- Database & Redis Setup
- Running the App
- Testing
- Database Design
- Authentication Architecture (Deep Dive)
- Celery — Current Status & Future Use
- Development Workflow
- Current Project Status
- Team & Acknowledgements

---

# 📌 Project Overview

NAGRIK AI is an AI-powered Civic Complaint Management Platform designed to modernize the interaction between citizens and government authorities.

Instead of manually managing complaints, the platform enables citizens to register complaints digitally, while government officials can efficiently review, assign, track, and resolve them using intelligent automation.

The platform integrates multiple backend technologies including asynchronous APIs, JWT authentication, Redis caching, Celery background jobs, and AI-powered services to provide a scalable and maintainable system.

This repository contains the backend implementation developed using **FastAPI** and follows a modular service-oriented architecture.

---

# ✨ Features

## Authentication — ✅ Complete

- JWT Authentication (Access + Refresh tokens, each with a unique `jti`)
- Real logout via Redis token blacklist (not just "delete the token client-side")
- Password hashing with bcrypt
- Email verification via OTP (HMAC-SHA256 hashed, Redis-backed, 5-minute expiry)
- Password reset via OTP (10-minute expiry, rate-limited to 3 requests/hour/email)
- Get / update own profile
- Change password (while logged in, separate from the OTP reset flow)
- Standard success/error response envelope with per-error error codes
- Role-Based Authorization — **Upcoming** (belongs to the Officer/Admin module)

## Complaint Management — Upcoming

- Register Complaint, Assign Complaint, Status Tracking, History, Resolution, Rejection, Citizen Rating

## Artificial Intelligence — Upcoming

- Complaint Priority Prediction, AI-powered Categorization, RAG chatbot, Semantic Search

## Notifications — Partially Scaffolded

- Redis-backed OTP storage — done
- Celery background workers — scaffolded, not yet wired (see the Celery section below)
- Complaint status notifications — upcoming

## Administration — Upcoming

- Admin Dashboard, Staff Dashboard, Complaint Assignment, User Management, Analytics

---

# 🛠 Technology Stack

## Backend
- FastAPI (async)
- Python 3.12
- SQLAlchemy 2.0 Async ORM
- Pydantic v2

## Database
- PostgreSQL 15
- AsyncPG (runtime) / Psycopg2 (sync, used by `test_db.py`)

## Authentication
- JWT (`python-jose`)
- bcrypt (`passlib`)
- `HTTPBearer` — a plain bearer-token scheme, not OAuth2 password-grant, since login takes a JSON body

## Background Processing
- Redis — OTP storage, token blacklist, rate limiting (all live today)
- Celery — declared dependency, scaffolding present, not yet wired to a real task (see the Celery section)

## AI Stack (Upcoming)
- Groq API, RAG, LangChain, FAISS

## Deployment (Upcoming)
- Docker, Nginx, Gunicorn/Uvicorn workers

---

# 🏗 High-Level System Architecture

```text
                         Citizen
                            │
                            ▼
                  FastAPI REST API
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
 Authentication      Complaint APIs      AI Services
   (complete)          (upcoming)          (upcoming)
       │                    │                    │
       ▼                    ▼                    ▼
 Security          Business Logic       RAG Engine
       │                    │
       └────────────┬───────┘
                     ▼
            PostgreSQL Database
                     │
      ┌──────────────┴──────────────┐
      ▼                             ▼
   Redis                      Celery Workers
      │                        (scaffolded,
      ▼                          not wired)
 OTP Storage
 Token Blacklist
 Rate Limiting
```

---

# 🔐 Authentication — Complete Reference

All protected endpoints require `Authorization: Bearer <access_token>`. Access tokens expire in **30 minutes**; refresh tokens in **7 days**. Every token carries a unique `jti`, which is what makes real, server-side logout possible.

| Method | Endpoint                | Description                                                      | Auth |
| ------ | ----------------------- | ---------------------------------------------------------------- | ---- |
| POST   | `/auth/register`        | Register a new citizen account, sends verification OTP           | ✗    |
| POST   | `/auth/verify-otp`      | Verify email using the OTP, activates the account                | ✗    |
| POST   | `/auth/login`           | Authenticate, returns access + refresh tokens                    | ✗    |
| POST   | `/auth/logout`          | Revoke the current access token (and refresh token, if supplied) | ✓    |
| POST   | `/auth/refresh`         | Exchange a valid refresh token for a new access token            | ✓    |
| GET    | `/auth/me`              | Get own profile                                                  | ✓    |
| PUT    | `/auth/me`              | Update own name/phone                                            | ✓    |
| POST   | `/auth/change-password` | Change password (already logged in)                              | ✓    |
| POST   | `/auth/forgot-password` | Request a password reset OTP (rate-limited)                      | ✗    |
| POST   | `/auth/reset-password`  | Complete password reset with OTP                                 | ✗    |

**OTP details**
- Verify-email OTP: valid 5 minutes
- Password-reset OTP: valid 10 minutes, and `forgot-password` is rate-limited to **3 requests per hour per email** — checked before the user lookup even happens, so it also can't be used to probe which emails are registered

**Logout details**
- Always revokes the access token used to call it
- Also revokes the refresh token if the client includes `refresh_token` in the request body — omitting it is a deliberate choice to only end the current session, not the whole login
- A revoked token can't be reused for anything, including calling logout again

**Error codes** (returned in every error response's `error_code` field)

| Code       | Meaning                                      | HTTP                                                      |
| ---------- | -------------------------------------------- | --------------------------------------------------------- |
| `AUTH_001` | Invalid credentials                          | 401                                                       |
| `AUTH_002` | Token expired                                | 401                                                       |
| `AUTH_003` | Token invalid (malformed/wrong type/revoked) | 401                                                       |
| `AUTH_004` | Insufficient permissions                     | 403 *(reserved — RBAC not yet implemented)*               |
| `AUTH_005` | Account inactive (deactivated)               | 403 *(reserved — admin deactivation not yet implemented)* |
| `AUTH_006` | Email not verified                           | 403                                                       |
| `AUTH_007` | Email already registered                     | 409                                                       |
| `AUTH_008` | Phone already registered                     | 409                                                       |
| `AUTH_009` | User not found                               | 404                                                       |
| `AUTH_010` | Invalid or expired OTP                       | 400                                                       |
| `AUTH_011` | Account already verified                     | 409                                                       |
| `RTE_001`  | Rate limit exceeded                          | 429                                                       |
| `VAL_001`  | Request validation failed                    | 422                                                       |

---

# 📦 Standard API Response Format

Every endpoint returns one of these two shapes.

**Success**
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "user": { "id": "...", "email": "...", "...": "..." }
  },
  "meta": null
}
```

**Error**
```json
{
  "success": false,
  "message": "Invalid email or password.",
  "error_code": "AUTH_001",
  "details": null
}
```

`data` is `null` for endpoints that only confirm an action (register, logout, change-password, etc.). `meta` is reserved for pagination on future list endpoints (complaints, notifications) and is always `null` today.

---

# 📂 Backend Project Structure

```text
Backend/
│
├── app/
│   │
│   ├── api/
│   │   ├── auth.py              ✅ 10 endpoints, fully wired
│   │   ├── complaints.py        stub
│   │   └── notifications.py     stub
│   │
│   ├── core/
│   │   ├── config.py            settings (DB, JWT, OTP, rate limit, SMTP, Redis, Celery)
│   │   ├── database.py          async SQLAlchemy session + get_db()
│   │   ├── security.py          password hashing, JWT create/decode, HTTPBearer scheme
│   │   ├── redis.py             Redis client singleton
│   │   ├── exception_handlers.py   global error → standard envelope mapping
│   │   └── celery_app.py        stub — Celery app not yet configured
│   │
│   ├── dependencies/
│   │   ├── auth.py              get_current_token_payload, get_current_user
│   │   └── roles.py             stub — role-based authorization, upcoming
│   │
│   ├── schemas/
│   │   ├── auth.py              all auth request/response schemas
│   │   ├── common.py            SuccessResponse[T] envelope
│   │   ├── complaint.py         stub
│   │   └── notification.py      stub
│   │
│   ├── services/
│   │   ├── auth_service.py       all auth business logic
│   │   ├── otp_service.py        OTP generate/verify, per-purpose expiry
│   │   ├── email_service.py      SMTP sending
│   │   ├── token_blacklist_service.py   Redis-backed logout/revocation
│   │   ├── rate_limit_service.py        generic Redis fixed-window limiter
│   │   └── notification_service.py      stub
│   │
│   ├── tasks/
│   │   ├── email_tasks.py        stub — intended future home for async email sending
│   │   └── notification_tasks.py stub
│   │
│   ├── utils/
│   │   ├── constants.py          roles, OTP purposes, token types
│   │   ├── exceptions.py         all custom exceptions, each with an error_code
│   │   └── validators.py         stub
│   │
│   ├── model.py                  User, Complaint, ComplaintUpdate, Notification, Rating, ChatSession
│   └── main.py                   FastAPI app, lifespan, router + exception handler registration
│
├── docs/                         extended documentation (see below)
├── requirements.txt
├── .env.example
├── new_test_auth_service_negative.py   18 tests, service-layer, no real email
├── test_auth_full_suite.py             40 tests, HTTP layer via httpx ASGITransport
├── test_auth_setup.py                  original infra smoke test
├── test_db.py                          table creation script
└── README.md
```

---

# 🚀 Getting Started

## Prerequisites

| Software   | Version |
| ---------- | ------- |
| Python     | 3.12+   |
| PostgreSQL | 14+     |
| Redis      | 7+      |
| Git        | Latest  |

## Clone & Checkout

```bash
git clone https://github.com/24f2000777/MAY2026-Team-059.git
cd MAY2026-Team-059
git checkout develop
# or the feature branch you're working on, e.g.:
git checkout feature/auth-foundation
```

## Virtual Environment

```bash
cd Backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

## Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install httpx                # needed for test_auth_full_suite.py, not yet in requirements.txt
```

---

# ⚙ Environment Configuration

```bash
cp .env.example .env
```

Then fill in:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@127.0.0.1:5432/nagrik_ai
SYNC_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@127.0.0.1:5432/nagrik_ai

# JWT
SECRET_KEY=YOUR_RANDOM_SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OTP — keep OTP_SECRET_KEY different from SECRET_KEY
OTP_SECRET_KEY=YOUR_RANDOM_OTP_SECRET
OTP_EXPIRE_SECONDS=300                      # optional, defaults to 300 (5 min)
RESET_PASSWORD_OTP_EXPIRE_SECONDS=600       # optional, defaults to 600 (10 min)
PASSWORD_RESET_RATE_LIMIT_MAX_ATTEMPTS=3    # optional, defaults to 3
PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS=3600  # optional, defaults to 3600 (1 hour)

# SMTP (Gmail example — SMTP_PASSWORD must be a Google App Password, not your login password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_google_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_FROM_NAME=NAGRIK AI

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery — configured but not yet wired to any real task, see the Celery section below
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI (upcoming module)
GROQ_API_KEY=YOUR_GROQ_API_KEY

# Application
ENVIRONMENT=development
DEBUG=True
```

Generate secrets with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

# 🐘 PostgreSQL & Redis Setup

```bash
# Postgres
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE DATABASE nagrik_ai;"

# Create tables
python test_db.py
# Expect: 6 tables — chat_sessions, complaint_updates, complaints, notifications, ratings, users

# Redis
sudo apt install redis-server
sudo systemctl enable --now redis-server
redis-cli ping   # expect: PONG
```

---

# 🌐 Running the App

Because email sending is processed in the background, you must run both the FastAPI server and the Celery worker in two separate terminals.

**Terminal 1: Start the Celery Worker**
```bash
cd Backend
source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
```

**Terminal 2: Start the FastAPI Server**
```bash
cd Backend
source venv/bin/activate
uvicorn app.main:app --reload
```

- App: http://127.0.0.1:8000
- Health check: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

**Testing auth in Swagger:** call `POST /auth/login`, copy the `access_token` from the response, click the padlock/**Authorize** button, paste just the token (no `Bearer ` prefix needed — Swagger adds it), then call any protected endpoint.

---

# 🧪 Testing

Two automated suites, 58 tests total, no real emails sent (SMTP is monkeypatched to capture OTPs in memory instead).

```bash
# 18 tests — calls auth_service functions directly
python new_test_auth_service_negative.py

# 40 tests — full HTTP layer via httpx, exercises routes + dependencies + exception handlers
python test_auth_full_suite.py
```

Both need Postgres and Redis running, same as the app itself. `test_auth_full_suite.py` additionally needs `pip install httpx`.

Coverage includes: every endpoint's happy path, duplicate email/phone, wrong/expired/reused OTPs, wrong password, unverified/inactive login, access-token-as-refresh-token, deleted-user refresh, rate-limit boundary (3 allowed, 4th rejected), profile update conflicts, and logout's full revocation behavior (access token revoked immediately, refresh token revoked only if supplied, double-logout rejected).

---

# 🗄 Database Design

Six core tables: **Users**, **Complaints**, **Complaint Updates**, **Notifications**, **Ratings**, **Chat Sessions**.

```mermaid
erDiagram
    USERS ||--o{ COMPLAINTS : files
    USERS ||--o{ COMPLAINTS : assigned_to
    USERS ||--o{ COMPLAINT_UPDATES : updates
    USERS ||--o{ RATINGS : gives
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ CHAT_SESSIONS : chats

    COMPLAINTS ||--o{ COMPLAINT_UPDATES : history
    COMPLAINTS ||--|| RATINGS : rating
    COMPLAINTS ||--o{ NOTIFICATIONS : triggers
    COMPLAINTS ||--o{ CHAT_SESSIONS : discussed
```

**Users** — `id, name, phone, email, role, hashed_password, is_active, created_at, updated_at`. `role` is one of `citizen` / `officer` / `admin`. `is_active` currently serves as the single "email verified" flag; account deactivation as a distinct future feature will need `AUTH_005` wired in separately (see the error code table above).

---

# 🔐 Authentication Architecture (Deep Dive)

```
API Route
   │
   ▼
auth_service.py  (business logic — no FastAPI imports here)
   │
   ├── security.py       password hashing, JWT create/decode
   ├── otp_service.py     OTP generate/verify (HMAC-SHA256, Redis, per-purpose TTL)
   ├── email_service.py    SMTP sending
   ├── token_blacklist_service.py   logout revocation
   └── rate_limit_service.py         forgot-password abuse prevention
   │
   ▼
Raises a custom exception on failure (utils/exceptions.py)
   │
   ▼
core/exception_handlers.py converts it to the standard error envelope
```

**Password security:** bcrypt, never stored or logged in plaintext.

**JWT:** two token types, distinguished by a `type` claim (`access` / `refresh`) so a refresh token can never be used where an access token is expected, and vice versa. Every token also carries a `jti` (unique id), enabling the logout blacklist.

```json
{
  "sub": "user_uuid",
  "role": "citizen",
  "type": "access",
  "jti": "3f9a1c2e...",
  "exp": 1750000000
}
```

**OTP:** generated in plaintext only to be emailed, never stored in plaintext — only its HMAC-SHA256 hash lives in Redis, with a TTL matching its purpose (5 min verify-email, 10 min password-reset). Verifying deletes the Redis entry immediately, so a given OTP can only ever be used once.

**Logout / revocation:** since JWTs are stateless, revoking one before its natural expiry requires a server-side record. `token_blacklist_service.py` stores `jti → revoked` in Redis with a TTL equal to the token's *remaining* lifetime, so entries clean themselves up — no manual purge job needed.

**Rate limiting:** `rate_limit_service.py` is a generic Redis fixed-window counter (`INCR` + `EXPIRE` on first hit), reusable later for other abuse-prone actions (e.g. login attempts) beyond just password reset.

---

# 🌱 Celery — Asynchronous Tasks

Celery is fully integrated and handles background processing to prevent long-running tasks from blocking API requests.

**Current Usage:**
- **Email Dispatch:** All verification and password-reset OTP emails are dispatched asynchronously via `send_email_task`. When a user requests an OTP, FastAPI generates the code, stores the hash in Redis, drops the email job into the Celery queue, and immediately returns a 200 OK. The Celery worker picks it up and executes the slow `smtplib` network call in the background.

**Future Use:**
- Scheduled complaint status escalations
- Generating heavy PDF reports
- Background AI priority scoring/RAG indexing

---

# 👨‍💻 Development Workflow

Feature-branch workflow: `feature/*` → `develop` → `main`. Never merge directly into `main`.

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
# ...work, commit in small meaningful chunks...
git push -u origin feature/your-feature-name
# open PR: feature/your-feature-name → develop
```

**Before opening a PR:** code compiles, no hardcoded secrets, README updated if paths/branches changed, tests pass, new dependencies added to `requirements.txt`, no leftover debug/notes files.

---

# 📌 Current Project Status

## ✅ Completed
- Backend foundation (FastAPI, async SQLAlchemy, PostgreSQL, Redis, config management)
- **Authentication — all 10 endpoints, logout with real revocation, rate limiting, standard response envelope, 58 passing tests**
- Database schema (all 6 tables)
- Health endpoint, Redis startup check, lifespan-based startup

## 🚧 In Progress / Next Up
- Citizen role-based authorization foundations (`dependencies/roles.py`)
- Complaint CRUD APIs

## 📋 Planned
- Complaint Management, Officer APIs, Admin APIs
- Notifications (Celery-backed)
- AI priority scoring, duplicate detection
- RAG Chatbot
- Dashboards & Analytics
- Docker / CI-CD
- **Module 11: Pre-Launch Security Audit**
  - Secret Leak Prevention
  - Personal Data Flow Audit
  - Pre-Deploy Production Audit
  - Deep Security Audit for Complex Logic
  - Attacker's Perspective Review

---

# 📚 Documentation

Extended docs live in `docs/`:

```
docs/
├── 01_project_overview.md
├── 02_architecture.md
├── 03_database.md
├── 04_authentication.md
├── 05_setup_guide.md
├── 06_api_design.md
├── 07_deployment.md
├── 08_git_workflow.md
└── 09_future_roadmap.md
```

---

# Team

**Team 059** • IIT Madras • Software Engineering • 2026

| Name              | Responsibility                                                 |
| ----------------- | -------------------------------------------------------------- |
| Amit Kumar Pandey | Backend Architecture, Authentication, Complaint APIs, Database |
| Akshit            | AI Engine, ML Priority Prediction, RAG Chatbot                 |
| Ravisha           | Testing, QA, Documentation                                     |

---

# License

Academic and educational purposes as part of IIT Madras Software Engineering coursework. All rights remain with the project contributors unless otherwise specified.

---

<div align="center">

## 🏛️ NAGRIK AI

**Building smarter civic services through Artificial Intelligence.**

⭐ If you found this project useful, consider giving the repository a star.

</div>