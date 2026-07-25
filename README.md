<div align="center">

# 🏛️ NAGRIK AI

### AI-Powered Civic Complaint Management Platform

> An intelligent civic grievance management platform that leverages Artificial Intelligence, Retrieval-Augmented Generation (RAG), asynchronous task processing, and modern frontend/backend engineering practices to streamline complaint registration, tracking, prioritization, and resolution.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)](https://vuejs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://sqlalchemy.org)

**Team 059** • IIT Madras • Software Engineering • 2026

</div>

---

This repository has two parts, developed in parallel and documented separately below:

- **`frontend/`** — a Vue 3 app, currently running on mock `localStorage` data (see [Frontend](#-frontend) below)
- **`Backend/`** — a FastAPI backend (see [Backend](#-backend) below)

They are not yet wired together. Connecting them is the next major integration step.

---

# 🖥 Frontend

A civic issue-reporting platform for citizens, municipal staff, and administrators, built with Vue 3. Citizens file complaints with photos and location pins, staff manage assigned tasks, and admins oversee everything with filters and analytics.

This is the **frontend only**. It currently runs on mock data stored in the browser's `localStorage`, no backend is connected yet.

## Tech Stack

- **Vue 3** - Composition API, `<script setup>`
- **Vue Router 4** - routing, role-based route guards
- **Pinia** - state management
- **Vite** - dev server and build tool
- No UI kit, no chart library - all charts (donut, line, bar) and styling are hand-built with SVG and CSS, kept dependency-light on purpose.

## Getting Started

### Requirements
- [Node.js](https://nodejs.org) 18 or later

### Install and run

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`).

### Build for production

```bash
npm run build
npm run preview   # serve the production build locally
```

## Demo Logins

Accounts are seeded automatically into `localStorage` the first time the app runs.

| Role    | Email                        | Password    |
|---------|-------------------------------|--------------|
| Citizen | citizen@nagrikai.app       | citizen123   |
| Staff   | ravi.staff@nagrikai.app    | staff123     |
| Admin   | admin@nagrikai.app         | admin123     |

You can also register a new citizen account from scratch (see **Auth Flow** below).

If login ever fails with correct-looking credentials after pulling new code, clear stale local data: DevTools → Application → Local Storage → delete `cr_users` and `cr_session` → refresh.

## Features

### Public / Landing
- Marketing landing page with hero, how-it-works, feature grid, Nagrik Saathi preview, and an "For Officials" section
- Glassmorphism footer (blurred translucent background)
- Public pages reachable without login: **FAQ**, **Privacy Policy**, **Terms of Service**, **Contact Us**
- A live demo of **Nagrik Saathi**

### Authentication
- **Register** — name, email, phone, password + confirm, with phone format validation and minimum password length
- **OTP verification** — a second step after registering; a demo one-time code is generated and shown on screen (no real SMS backend exists yet)
- **Login** — email + password, redirects to the correct dashboard by role
- **Forgot / Reset Password** — email lookup, then set a new password (mocked — no real email delivery)

### Citizen
- Dashboard with a personalized greeting, quick-action tiles, and KPI cards (Total / Submitted / In Progress / Resolved)
- **Report an Issue** — category, description, severity, photo upload, click-to-pin map
- **My Complaints** — card list with status/severity badges
- **Complaint Detail** — full status timeline; once resolved, **Rate & Review** the resolution (star rating + comment)
- **My Activity (Analytics)** — status donut chart, category bar chart, resolution rate

### Staff
- Dashboard with assigned tasks sorted by priority, KPI cards
- **Update Task** — change status, add notes, view history - guarded against crashing on an invalid complaint id
- **My Performance (Analytics)** - status donut chart, category breakdown, average resolution time

### Admin
- Dashboard with KPI cards (Total / Unassigned / High Priority Open / Resolved) and a filterable data table (status, category, area, date)
- **Assign / Reassign** complaints to staff
- **Analytics** — KPI cards, 14-day filing trend line chart, status donut chart, category and resolution-time bar charts, complaint density heatmap by area — all with entrance animation

### Shared (any logged-in role)
- **Nagrik Saathi** - a scripted keyword-matched chatbot demo (not a real AI assistant unless functioanlity added)
- **Notifications** - a feed of recent status changes relevant to the logged-in user's role
- **Profile** - edit name/phone, change password
- **Feedback** - general app feedback form with a 1–5 rating
- Custom **404** page for any unmatched route

## Folder Structure

```
frontend/src/
├── pages/
│   ├── LandingPage.vue
│   ├── Login.vue / Register.vue / VerifyOtp.vue
│   ├── ForgotPassword.vue / ResetPassword.vue
│   ├── CitizenDashboard.vue / SubmitComplaint.vue / ComplaintDetail.vue / RateReview.vue /CitizenAnalytics.vue
│   ├── StaffDashboard.vue / ComplaintUpdate.vue / StaffAnalytics.vue
│   ├── AdminDashboard.vue / AssignmentPage.vue / AnalyticsPage.vue
│   ├── NagrikSaathi.vue / Notifications.vue / Profile.vue / FeedbackReport.vue
│   ├── Faqs.vue / PrivacyPolicy.vue / TermsOfService.vue / ContactUs.vue
│   └── NotFound.vue
├── components/
│   ├── Navbar.vue / DashboardHero.vue / ActionTile.vue / footer.vue
│   ├── ComplaintCard.vue / StatusBadge.vue / StatCard.vue
│   └── DonutChart.vue / LineChart.vue
├── stores/          Pinia: authStore.js, complaintStore.js
├── api/client.js    Mock data layer (see below)
├── router/index.js  All routes + role-based guards
└── assets/style.css Global styling
```

## About the Mock Data Layer

`src/api/client.js` simulates a backend using `localStorage`. It is clearly commented as mock-only at the top of the file. Every exported function (`registerUser`, `loginUser`, `getComplaints`, `createComplaint`, etc.) is written to match what a real REST endpoint would expect, so connecting a real backend later means rewriting the function bodies in this one file. No other file needs to change.

Things that are explicitly **not real** right now, by design:
- Passwords are stored in plaintext in `localStorage`
- OTP codes are generated client-side and displayed on screen, not sent via SMS/email
- Password reset has no email/token step — reaching the reset screen is treated as proof of ownership
- Nagrik Saathi is a scripted, keyword-matched demo, not a real AI, till backend with relevant functionality is connected.

## Placeholders

A few landing-page footer links intentionally go nowhere yet, since either no corresponding feature exists or login is required to use the same: "Try Nagrik Saathi" chatbot demo is wired up, but points back to login due to requirement.

---

# ⚙️ Backend

> An intelligent civic grievance management platform that leverages Artificial Intelligence, Retrieval-Augmented Generation (RAG), asynchronous task processing, and modern backend engineering practices to streamline complaint registration, tracking, prioritization, and resolution.

*A scalable backend for intelligent civic complaint management.*

## 📖 Table of Contents

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

## 📌 Project Overview

NAGRIK AI is an AI-powered Civic Complaint Management Platform designed to modernize the interaction between citizens and government authorities.

Instead of manually managing complaints, the platform enables citizens to register complaints digitally, while government officials can efficiently review, assign, track, and resolve them using intelligent automation.

The platform integrates multiple backend technologies including asynchronous APIs, JWT authentication, Redis caching, Celery background jobs, and AI-powered services to provide a scalable and maintainable system.

This section covers the backend, implemented using **FastAPI** and following a modular service-oriented architecture.

---

## ✨ Features

### Authentication — ✅ Complete
- JWT Authentication (Access + Refresh tokens, each with a unique `jti`)
- Real logout via Redis token blacklist (not just "delete the token client-side")
- Password hashing with bcrypt
- Email verification via OTP (HMAC-SHA256 hashed, Redis-backed, 5-minute expiry)
- Password reset via OTP (10-minute expiry, rate-limited to 3 requests/hour/email)
- Get / update own profile
- Change password (while logged in, separate from the OTP reset flow)
- Standard success/error response envelope with per-error error codes
- Role-Based Authorization — ✅ Complete (`require_roles()` dependency factory)

### AI Priority Scoring, Categorization, Routing, RAG Chatbot, Duplicate Detection — ✅ Complete
- `/ml/priority/*`, `/ml/categorize/*`, `/ml/route-department/*`, `/ml/high-risk`, `/ml/check-duplicate`, `/ml/duplicates/*`
- `/chat/message`, `/chat/history/{session_id}` — Nagrik Saathi RAG chatbot

### Complaint Management — Upcoming
- Register Complaint, Assign Complaint, Status Tracking, History, Resolution, Rejection, Citizen Rating

### Notifications — Schema ready, endpoints upcoming
- `Notification` model exists; `GET/PATCH /notifications` endpoints not yet implemented

### Administration — Partially built
- Admin/staff/citizen dashboards done; assignment, user management, and full analytics upcoming

---

## 🛠 Technology Stack

**Backend:** FastAPI (async), Python 3.12, SQLAlchemy 2.0 Async ORM, Pydantic v2
**Database:** PostgreSQL 15, AsyncPG (runtime) / Psycopg2 (sync, used by `test_db.py`)
**Authentication:** JWT (`python-jose`), bcrypt (`passlib`), `HTTPBearer`
**Background Processing:** Redis (OTP storage, token blacklist, rate limiting), Celery (nightly priority rescore, email dispatch)
**AI Stack:** Groq / Gemini / HuggingFace (with fallback chain), LangChain, LangGraph, FAISS, sentence-transformers

---

## 🔐 Authentication — Complete Reference

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

| Code       | Meaning                                      | HTTP |
| ---------- | --------------------------------------------- | ---- |
| `AUTH_001` | Invalid credentials                          | 401  |
| `AUTH_002` | Token expired                                | 401  |
| `AUTH_003` | Token invalid (malformed/wrong type/revoked) | 401  |
| `AUTH_004` | Insufficient permissions                     | 403  |
| `AUTH_005` | Account inactive (deactivated)               | 403 *(reserved — admin deactivation not yet implemented)* |
| `AUTH_006` | Email not verified                           | 403  |
| `AUTH_007` | Email already registered                     | 409  |
| `AUTH_008` | Phone already registered                     | 409  |
| `AUTH_009` | User not found                               | 404  |
| `AUTH_010` | Invalid or expired OTP                       | 400  |
| `AUTH_011` | Account already verified                     | 409  |
| `AUTH_012` | Chat session belongs to another user         | 403  |
| `RTE_001`  | Rate limit exceeded                          | 429  |
| `VAL_001`  | Request validation failed                    | 422  |
| `VAL_002`  | Location: lat/lng given without the other    | 422  |

---

## 📦 Standard API Response Format

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

## 📂 Backend Project Structure

```text
Backend/
│
├── app/
│   │
│   ├── api/
│   │   ├── auth.py              ✅ 10 endpoints, fully wired
│   │   ├── ml.py                ✅ 10 endpoints, priority/category/routing/duplicate detection
│   │   ├── chat.py              ✅ 2 endpoints, Nagrik Saathi
│   │   ├── dashboard.py         ✅ 4 endpoints, role-based views
│   │   ├── complaints.py        stub (debug /whoami only)
│   │   └── notifications.py     stub
│   │
│   ├── chatbot/                 conversation_graph.py, providers.py, extractor.py, knowledge_base.py (RAG)
│   │
│   ├── core/
│   │   ├── config.py            settings (DB, JWT, OTP, rate limit, SMTP, Redis, Celery, CORS)
│   │   ├── database.py          async SQLAlchemy session + get_db()
│   │   ├── security.py          password hashing, JWT create/decode, HTTPBearer scheme
│   │   ├── redis.py             Redis client singleton
│   │   ├── exception_handlers.py   global error → standard envelope mapping
│   │   └── celery_app.py        Celery app + nightly beat schedule
│   │
│   ├── dependencies/
│   │   ├── auth.py              get_current_token_payload, get_current_user
│   │   └── roles.py             require_roles() — role-based authorization, ✅ complete
│   │
│   ├── schemas/
│   │   ├── auth.py              all auth request/response schemas
│   │   ├── common.py            SuccessResponse[T] envelope
│   │   ├── complaint.py         ComplaintCreate/Location/Response schemas (not yet wired to an endpoint)
│   │   └── notification.py      stub
│   │
│   ├── services/
│   │   ├── auth_service.py       all auth business logic
│   │   ├── otp_service.py        OTP generate/verify, per-purpose expiry
│   │   ├── email_service.py      SMTP sending
│   │   ├── token_blacklist_service.py   Redis-backed logout/revocation
│   │   ├── rate_limit_service.py        generic Redis fixed-window limiter
│   │   ├── priority_service.py   ML priority scoring
│   │   ├── category_service.py   LLM-based category prediction
│   │   ├── routing_service.py    department routing
│   │   ├── duplicate_service.py  embedding-based duplicate detection
│   │   ├── chat_service.py       Nagrik Saathi persistence
│   │   ├── risk_alert_service.py high-risk complaint flagging
│   │   └── notification_service.py      stub
│   │
│   ├── tasks/
│   │   ├── email_tasks.py        async email sending
│   │   ├── priority_tasks.py     nightly rescore job
│   │   └── notification_tasks.py stub
│   │
│   ├── utils/
│   │   ├── constants.py          roles, OTP purposes, token types, departments
│   │   ├── exceptions.py         all custom exceptions, each with an error_code
│   │   └── validators.py         stub
│   │
│   ├── model.py                  User, Complaint, ComplaintUpdate, Notification, Rating, ChatSession, Department
│   └── main.py                   FastAPI app, lifespan, router + exception handler registration
│
├── Testing/                      pytest suite — 81 passing tests
├── docs/                         extended documentation (see below)
├── requirements.txt
├── .env.example
└── openapi.yaml                  generated Swagger/OpenAPI spec (from app.openapi())
```

---

## 🚀 Getting Started

### Prerequisites

| Software   | Version |
| ---------- | ------- |
| Python     | 3.12+   |
| PostgreSQL | 14+     |
| Redis      | 7+      |
| Git        | Latest  |

### Clone & Checkout

```bash
git clone https://github.com/24f2000777/MAY2026-Team-059.git
cd MAY2026-Team-059
git checkout develop
```

### Virtual Environment

```bash
cd Backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ⚙ Environment Configuration

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

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI providers
GROQ_API_KEY=YOUR_GROQ_API_KEY
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
HUGGINGFACE_API_KEY=YOUR_HUGGINGFACE_API_KEY

# CORS (frontend origins allowed to call this API)
FRONTEND_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Application
ENVIRONMENT=development
DEBUG=True
```

Generate secrets with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🐘 PostgreSQL & Redis Setup

```bash
# Postgres
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE DATABASE nagrik_ai;"

# Redis
sudo apt install redis-server
sudo systemctl enable --now redis-server
redis-cli ping   # expect: PONG
```

---

## 🌐 Running the App

Because email sending and the nightly priority rescore are processed in the background, run both the FastAPI server and the Celery worker (plus beat, for the nightly job) in separate terminals.

**Terminal 1: Celery Worker**
```bash
cd Backend
source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
```

**Terminal 2: Celery Beat (nightly priority rescore, 2 AM IST)**
```bash
cd Backend
source venv/bin/activate
celery -A app.core.celery_app beat --loglevel=info
```

**Terminal 3: FastAPI Server**
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

## 🧪 Testing

```bash
cd Backend
pytest
```

81 passing tests across auth (50, full HTTP layer via httpx `ASGITransport`), priority scoring, categorization/routing, duplicate detection, chatbot persistence, and risk alerting. Needs Postgres and Redis running, same as the app itself. No real emails or LLM calls are mocked away where the test's whole point is proving real behavior (see each suite's own docstring).

---

## 🗄 Database Design

Seven core tables: **Users**, **Complaints**, **Complaint Updates**, **Notifications**, **Ratings**, **Chat Sessions**, **Departments**.

```mermaid
erDiagram
    USERS ||--o{ COMPLAINTS : files
    USERS ||--o{ COMPLAINTS : assigned_to
    USERS ||--o{ COMPLAINT_UPDATES : updates
    USERS ||--o{ RATINGS : gives
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ CHAT_SESSIONS : chats
    DEPARTMENTS ||--o{ COMPLAINTS : routed_to

    COMPLAINTS ||--o{ COMPLAINT_UPDATES : history
    COMPLAINTS ||--|| RATINGS : rating
    COMPLAINTS ||--o{ NOTIFICATIONS : triggers
    COMPLAINTS ||--o{ CHAT_SESSIONS : discussed
```

**Users** — `id, name, phone, email, role, hashed_password, is_active, department_id, created_at, updated_at`. `role` is one of `citizen` / `staff` / `admin`.

---

## 🔐 Authentication Architecture (Deep Dive)

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

## 🌱 Celery — Asynchronous Tasks

**Current Usage:**
- **Email Dispatch:** All verification and password-reset OTP emails are dispatched asynchronously via `send_email_task`.
- **Nightly Priority Rescore:** Celery Beat runs `rescore_all_complaints_task` at 2 AM IST, recomputing `priority_score` for every complaint.

**Future Use:**
- Notification creation on complaint status change
- Scheduled complaint auto-close (7-day window)
- Generating heavy PDF reports

---

## 👨‍💻 Development Workflow

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

## 📌 Current Project Status

### ✅ Completed
- Auth (10 endpoints), RBAC, ML priority scoring, categorization, department routing, duplicate detection, RAG chatbot — 81 passing tests
- Database schema (all 7 tables)
- Frontend (Vue 3, all pages) — running on mock data

### 🚧 In Progress / Next Up
- Wiring the frontend to the real backend (currently on mock `localStorage` data)
- Complaint CRUD (create/list/get) — schema exists, endpoints don't yet

### 📋 Planned
- Complaint state machine (approve/start/resolve/reject), assignment, internal notes
- Notifications endpoints (model exists, endpoints don't)
- Complaint closure + auto-close
- Photo evidence upload, ratings endpoint
- Docker / CI-CD

---

## 📚 Documentation

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

## Team

**Team 059** • IIT Madras • Software Engineering • 2026

| Name              | Responsibility                                                 |
| ----------------- | -------------------------------------------------------------- |
| Amit Kumar Pandey | Backend Architecture, Authentication, Complaint APIs, Database |
| Akshit            | AI Engine, ML Priority Prediction, RAG Chatbot                 |
| Ravisha           | Testing, QA, Complaint Schema, Documentation                    |
| Lakshay Bansal    | Frontend (Vue 3) — pages, routing, auth store                  |
| Arubhi Bansal     | Scrum master, frontend support                                 |

---

## License

Academic and educational purposes as part of IIT Madras Software Engineering coursework. All rights remain with the project contributors unless otherwise specified.

<div align="center">

**Building smarter civic services through Artificial Intelligence.**

⭐ If you found this project useful, consider giving the repository a star.

</div>
