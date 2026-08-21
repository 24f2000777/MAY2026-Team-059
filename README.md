<div align="center">

# 🏛️ NAGRIK AI

### Report a civic problem. Know it's being fixed. Stop chasing anyone for updates.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)](https://vuejs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)

**Team 059** · IIT Madras · Software Engineering · 2026

</div>

---

## 🕳️ The problem

Most municipal complaint systems are a phone line, a WhatsApp number, and a form nobody checks. Nothing is connected. Complaints get lost, duplicated, or sent to the wrong desk, and citizens are left guessing whether anyone is even looking.

**NAGRIK AI replaces that with one connected system.** Report an issue once, in your own words if you want. An AI reads it, scores how urgent it is, and routes it to the right department automatically. From there you can watch it move through every stage and get notified the moment anything changes.

---

## 🙋 Who this is for

**👤 Citizens** report a problem in seconds, by form or by chatting with **Nagrik Saathi**, an AI assistant that files the complaint for you. Attach a photo and your location, track it live, get notified at every step, and confirm the fix yourself before it's closed.

**👷 Municipal staff** get one task list instead of a phone call, with a real address, photo, and priority score for every assignment. Start work, mark it resolved, attach proof once it's fixed.

**🧑‍💼 Administrators** get a live dashboard of every complaint, one-click approve/reject/assign pulling from a real staff list, automatic high-risk flagging, and full account and department control.

---

## 🧭 How it works

1. You describe the problem, by form or by talking to Nagrik Saathi.
2. The AI classifies it, scores its urgency, and checks it isn't a duplicate.
3. It's routed automatically to the correct department.
4. Staff get assigned and see your evidence and location before heading out.
5. You're notified at every status change: approved, assigned, started, resolved.
6. You confirm the fix yourself and leave a rating.

Every step is real. Nothing here is simulated for a demo.

---

## ✨ What makes it different

| | |
|---|---|
| 🤖 **Talk to it, don't fill forms** | Nagrik Saathi understands plain language complaints. |
| 📍 **Evidence that helps** | Photos and GPS travel with the complaint, so staff go to the right place. |
| ⚡ **Real urgency scoring** | An AI engine flags genuinely dangerous complaints automatically. |
| 🔔 **You're never left wondering** | Automatic notifications on every status change. |
| 🗺️ **One shared source of truth** | Citizens, staff, and admins see the same real data. |
| ✅ **Citizens get the final word** | A complaint can't be closed without your confirmation. |

---

## 🔑 Try it yourself

Everyone on this project shares one demo admin account, since we all point at the same database.

```
email:    admin@nagrikai.team
password: TestPass123!
```

> [!WARNING]
> This account can manage every user and permanently delete complaints. Please don't share it anywhere public. You can also register your own free citizen account any time.

---

## 🛠️ Setup instructions

Everything below is written so it works whether this is the first backend project you've ever set up or your fiftieth. Follow it top to bottom, in order.

### Step 0: Install the prerequisites

You need five things installed: **Python 3.12+**, **Node.js 18+**, **PostgreSQL** (or a free Supabase account, see below), **Redis**, and **Git**.

<details>
<summary><strong>macOS</strong></summary>

Install [Homebrew](https://brew.sh) first if you don't have it, then:

```bash
brew install python@3.12 node git redis
brew services start redis
```

You don't need a local PostgreSQL install if you're using Supabase (recommended, see Step 2). If you want Postgres running locally instead: `brew install postgresql@16 && brew services start postgresql@16`.

</details>

<details>
<summary><strong>Windows</strong></summary>

Install [Python 3.12+](https://www.python.org/downloads/) (tick "Add Python to PATH" during install), [Node.js LTS](https://nodejs.org), and [Git](https://git-scm.com/download/win) from their official installers.

For Redis, the simplest route on Windows is [Memurai](https://www.memurai.com/) (a native Redis-compatible server) or running Redis inside [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install):

```powershell
wsl --install
# inside the WSL terminal:
sudo apt update && sudo apt install redis-server -y
sudo service redis-server start
```

Run every command in this guide from either PowerShell (backend and frontend commands work the same) or inside WSL.

</details>

<details>
<summary><strong>Linux (Debian/Ubuntu)</strong></summary>

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv nodejs npm git redis-server -y
sudo systemctl enable redis-server --now
```

If your distro's default Node.js is older than 18, install it via [nvm](https://github.com/nvm-sh/nvm) instead: `nvm install 18 && nvm use 18`.

</details>

Confirm everything installed correctly:

```bash
python3 --version    # 3.12 or higher
node --version        # v18 or higher
git --version
redis-cli ping        # must print PONG once Redis is running
```

### Step 1: Clone the repository

```bash
git clone https://github.com/24f2000777/MAY2026-Team-059.git
cd MAY2026-Team-059
```

### Step 2: Set up the database

You have two options. **Supabase is recommended**, it's free, requires no local Postgres install, and is what the whole team uses.

**Option A: Supabase (recommended)**
1. Create a free account at [supabase.com](https://supabase.com) and create a new project.
2. In your project, go to **Connect** (top of the dashboard).
3. Copy the **Transaction pooler** connection string, this becomes your `DATABASE_URL`.
4. Copy the **Session pooler** connection string, this becomes your `SYNC_DATABASE_URL`.
5. Do **not** use the "Direct connection" string, it only resolves over IPv6 and fails with `could not translate host name` on many networks and ISPs.

**Option B: Local PostgreSQL**
1. Create a database: `createdb nagrikai`
2. Your connection strings both point at it, just with different drivers: `postgresql+asyncpg://user:pass@localhost/nagrikai` for `DATABASE_URL`, `postgresql://user:pass@localhost/nagrikai` for `SYNC_DATABASE_URL`.

### Step 3: Configure the backend

```bash
cd Backend
python3 -m venv venv
source venv/bin/activate          # Windows (PowerShell): venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

> [!NOTE]
> This install step downloads a lot, the AI and ML libraries are large. A few minutes on a normal connection is expected, it isn't stuck.

Copy the example environment file and fill it in:

```bash
cp .env.example .env
```

| Variable | What to put | Required? |
|---|---|---|
| `DATABASE_URL` | The **Transaction pooler** string from Step 2 | Yes |
| `SYNC_DATABASE_URL` | The **Session pooler** string from Step 2 | Yes |
| `SECRET_KEY` | A random 32+ character string. Generate one with `python3 -c "import secrets; print(secrets.token_hex(32))"` | Yes |
| `OTP_SECRET_KEY` | A second, different random string, same command as above | Yes |
| `GROQ_API_KEY` | Free key from [console.groq.com](https://console.groq.com/keys). Powers the chatbot and priority scoring | Yes |
| `GEMINI_API_KEY` / `HUGGINGFACE_API_KEY` | Optional automatic fallbacks if Groq is rate-limited | No |
| SMTP settings | Leave exactly as shipped. `.env.example` already has real, working Ethereal test-inbox credentials, real email is never sent | No changes needed |
| `REDIS_URL` | `redis://localhost:6379/0` if Redis is running locally, no setup needed | Yes |

Run the database migrations, this creates every table:

```bash
alembic upgrade head
```

### Step 4: Start the backend

The backend needs **three terminals running at once**, each with the virtual environment activated (`source venv/bin/activate`, or on Windows `venv\Scripts\Activate.ps1`).

| Terminal | Command | What it does |
|---|---|---|
| 1 | `celery -A app.core.celery_app worker --loglevel=info` | Sends OTP verification and password reset emails |
| 2 | `celery -A app.core.celery_app beat --loglevel=info` | Runs the nightly priority rescore. Optional if you're just testing locally |
| 3 | `uvicorn app.main:app --reload` | The actual API server, at `http://127.0.0.1:8000` |

Once terminal 3 shows "Application startup complete", open **`http://127.0.0.1:8000/docs`** in a browser. If you see the Swagger UI, the backend is alive.

### Step 5: Start the frontend

In a fourth terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL it prints, almost always **`http://localhost:5173`**. Log in with the shared demo admin above, or register your own citizen account.

### If something goes wrong

| You see this | It means this | Fix |
|---|---|---|
| `Address already in use` | An old server is still running on that port | `lsof -nP -iTCP:8000 -sTCP:LISTEN` then `kill <pid>` (swap `8000` for `5173` for the frontend). On Windows: `netstat -ano \| findstr :8000` then `taskkill /PID <pid> /F` |
| Login says it can't reach the server | Frontend and backend are on mismatched ports | The backend only accepts requests from `5173` or `3000`. If Vite printed `5174` instead because `5173` was busy, free `5173` and restart it |
| OTP email never arrives | The Celery worker (Terminal 1) isn't running, or SMTP is misconfigured | Start Terminal 1, or confirm `.env` still has the real Ethereal values from `.env.example`, don't replace them with a real email provider unless you mean to |
| `column does not exist` or a missing table | Your database schema is behind | `cd Backend && alembic upgrade head` |
| `could not translate host name "db.....supabase.co"` | `SYNC_DATABASE_URL` is set to Supabase's "Direct connection" string | Swap it for the **Session pooler** string instead, see Step 2 |
| `redis-cli ping` doesn't print `PONG` | Redis isn't running | macOS: `brew services start redis`. Linux: `sudo systemctl start redis-server`. Windows: start Memurai or your WSL Redis service |
| `pip install -r requirements.txt` fails on an ML library | Usually a missing system compiler or an outdated `pip` | Run `pip install --upgrade pip setuptools wheel` first, then retry |
| `create_admin` script refuses to run | Working as intended, only one admin account is allowed at a time | Use the shared demo login above instead |
| Chatbot hangs or never replies | The AI provider hit a rate limit | Wait a minute and retry, or add `GEMINI_API_KEY`/`HUGGINGFACE_API_KEY` to `.env` as fallbacks |
| You see complaints or accounts you didn't create | Expected, this is a shared team database | Don't delete anything that isn't clearly yours without asking first |

---

## 💡 What's new lately

A full visual redesign across every dashboard, a faster admin experience, staff photo proof-of-resolution, and the chatbot now links straight to the complaint you just filed. Full changelog below.

---

<details>
<summary><strong>📚 Full technical reference: every API endpoint, error codes, database schema, and how the team works</strong></summary>

## Frontend reference

A Vue 3 app for citizens, staff, and admins. Vue 3.5 with `<script setup>`, Vue Router 5 with role based guards, Pinia 3, Vite 8. No UI kit, no chart library, every chart is hand built SVG.

### What's real vs sample data

| API file | Talks to |
|---|---|
| `api/authApi.js` | Real backend, register, verify, resend, login, logout |
| `api/chatApi.js` | Real backend, Nagrik Saathi, real AI replies |
| `api/complaintApi.js` | Real backend, submission, listing, detail, every lifecycle transition, attachments, feedback, officer list |
| `api/notificationApi.js` | Real backend, listing, unread count, mark read, delete, preferences |
| `api/analyticsApi.js` | Real backend, `GET /analytics/summary`, scoped by role (citizen sees their own filings, staff their assignments, admin everything) |
| `api/client.js` | Sample data, only `FeedbackReport.vue` still uses it |

`FeedbackReport.vue` is a deliberate gap, not an oversight. The real feedback system is always a rating on one specific resolved complaint, there's no endpoint for untargeted app feedback yet.

### What each role can do

- **Citizens:** real dashboard (`GET /complaints/mine`), a real submit form with map-based location picking, real complaint detail with status, history, attachments, and a real rating flow. Can also delete their own complaint while it's still "submitted", or withdraw it after approval.
- **Staff:** real task list (`GET /complaints?assigned_to=`), contextual Start Work / Mark Resolved buttons that match the actual state machine, not a free-form dropdown.
- **Admins:** real dashboard, real Approve/Reject and Assign/Reassign actions pulling a real staff list from `GET /admin/officers`. Fetches every page of complaints, not capped at 100.
- **Everyone:** a real notifications feed with mark read / mark all read / delete, plus a live unread badge and dashboard reminder banner.

### Folder layout

```
frontend/src/
├── pages/          LandingPage, Login, Register, VerifyOtp, CitizenDashboard, SubmitComplaint,
│                   ComplaintDetail, RateReview, StaffDashboard, ComplaintUpdate, AdminDashboard,
│                   AssignmentPage, NagrikSaathi, Notifications, Profile, FeedbackReport (sample),
│                   AnalyticsPage/CitizenAnalytics/StaffAnalytics, Faqs, PrivacyPolicy, etc.
├── components/     Navbar, DashboardHero, ActionTile, ComplaintCard, StatusBadge, StatCard, DonutChart,
│                   LineChart, NotificationBanner
├── stores/         authStore.js, chatStore.js, notificationStore.js (all real)
├── api/            client.js (sample), httpClient.js (real fetch wrapper, handles multipart), authApi.js,
│                   chatApi.js, complaintApi.js, notificationApi.js, analyticsApi.js (all real)
├── router/index.js
└── assets/style.css
```

Most complaint pages call `complaintApi.js`/`notificationApi.js` directly from their own `onMounted` hook with local `ref` state, rather than through a shared store. That was a deliberate choice over retrofitting the old synchronous mock store for real async calls.

## Backend reference

FastAPI, async throughout, SQLAlchemy 2.0 with asyncpg, JWT auth, Redis for OTP/rate limiting/token revocation, Celery for background email and the nightly rescore, Alembic for migrations, LangGraph for the chatbot with real retrieval augmented answers. Groq is the primary AI provider, Gemini and HuggingFace are automatic fallbacks.

Every protected endpoint expects `Authorization: Bearer <access_token>`. Access tokens last 30 minutes, refresh tokens 7 days.

**Response envelope:**
```json
{ "success": true, "message": "Login successful.", "data": { "...": "..." }, "meta": null }
{ "success": false, "message": "Invalid email or password.", "error_code": "AUTH_001", "details": null }
```

### Endpoints

**`/auth`:** `POST /register`, `/verify-otp`, `/resend-otp`, `/login`, `/refresh`, `/logout`, `GET /me`, `PUT /me`, `POST /change-password`, `/forgot-password`, `/reset-password`

**`/admin`:** `POST /users` (create staff), `GET /officers` (list staff, for an assignment dropdown), `GET`/`POST /departments`, `PATCH`/`DELETE /departments/{id}`, `GET /users` (list, any role, filterable/paginated), `GET /users/{id}` (detail, includes their complaints), `PATCH /users/{id}/status` (activate/deactivate), `PATCH /users/{id}/role`, `PATCH /users/{id}/department` (reassign staff), `GET /export` (CSV, same filters as `GET /complaints`). All admin only. No endpoint creates the admin itself, see `scripts/create_admin.py`.

**`/complaints`:** `POST` (create), `GET` (list, role filtered), `GET /mine`, `GET /wards`, `GET /ward/{id}`, `GET /category/{category}`, `GET /{id}`, `PATCH /{id}` (edit), `DELETE /{id}` (admin, any complaint; or the owning citizen, only while still "submitted"), `GET /{id}/history`, `GET`/`POST /{id}/updates` (internal notes), `PATCH /{id}/approve`, `/reject`, `/assign`, `/start`, `/resolve`, `/withdraw`, `/close`, `GET`/`POST /{id}/attachments` (`purpose: citizen_evidence` by default, or `resolution_proof` for a staff-uploaded proof-of-fix photo once resolved), `GET`/`POST /{id}/feedback`

**`/attachments`:** `GET`/`DELETE /{id}`

**`/notifications`:** `GET`, `GET /unread-count`, `PATCH /read-all`, `PATCH /{id}/read`, `DELETE /{id}`, `POST /preferences`. Created synchronously, in the same request, no background job.

**`/feedback`:** `GET /officer/{id}`, `GET /summary` (both admin only)

**`/analytics`:** `GET /summary`, role-scoped complaint volume and status breakdown (citizen sees their own filings, staff their assignments, admin everything)

**`/chat`:** `POST /message`, `GET /history/{session_id}`

**`/ml`:** `GET`/`POST /priority/{id}`, `POST /rescore-all`, `GET`/`POST /categorize/{id}`, `GET`/`POST /route-department/{id}`, `GET /high-risk`, `POST /check-duplicate`, `GET /duplicates/{id}`

**`/dashboard`:** `GET /citizen`, `/staff`, `/admin`, `/internal`

### The complaint state machine

```
submitted --approve--> approved --start--> in_progress --resolve--> resolved --close--> closed
    \                       \
     \--reject--> rejected   \--reject--> rejected

submitted --withdraw--> withdrawn
```

Approve/reject are admin only. Start/resolve need the complaint assigned, and a staff caller must be the actual assignee. Withdraw/close are citizen-only, on their own complaint. Feedback is an alternate path to close that also leaves a rating.

### Error codes

| Code | Meaning | HTTP |
|---|---|---|
| AUTH_001 | Wrong email/password | 401 |
| AUTH_002 | Token expired | 401 |
| AUTH_003 | Token invalid, malformed, or revoked | 401 |
| AUTH_004 | No permission | 403 |
| AUTH_005 | Account inactive | 403 |
| AUTH_006 | Email not verified | 403 |
| AUTH_007 | Email already registered | 409 |
| AUTH_008 | Phone already registered | 409 |
| AUTH_009 | User not found | 404 |
| AUTH_010 | OTP invalid/expired | 400 |
| AUTH_011 | Account already verified | 409 |
| AUTH_012 | Chat session belongs to someone else | 403 |
| COMP_001 | Complaint not found | 404 |
| COMP_002 | Not a real staff account | 422 |
| COMP_003 | Already terminal, nothing to assign | 409 |
| COMP_004 | Transition not allowed from current status | 409 |
| COMP_005 | Not the assigned staff member | 403 |
| COMP_006 | Not your complaint | 403 |
| COMP_007 | Already rated | 409 |
| COMP_008 | Not currently resolved | 409 |
| FILE_001 | File too large | 413 |
| FILE_002 | Unsupported/spoofed file type | 415 |
| FILE_003 | Max attachments reached | 409 |
| FILE_004 | Attachment not found | 404 |
| NOTIF_001 | Notification not found or not yours | 404 |
| RTE_001 | Rate limit exceeded | 429 |
| VAL_001 | No address or coordinates given | 422 |
| VAL_002 | Only one of latitude/longitude given | 422 |

### Backend folder layout

```
Backend/
├── app/
│   ├── api/            auth, admin, complaints, attachments, notifications, feedback, chat, ml, dashboard
│   ├── chatbot/         conversation_graph, extractor, knowledge_base, providers
│   ├── core/             config, database, security, redis, exception_handlers, celery_app
│   ├── dependencies/     auth (get_current_user), roles (require_roles)
│   ├── schemas/           auth, common, complaint, chat, notification, feedback, admin
│   ├── services/           one per domain, plus priority/category/routing/duplicate/risk_alert services
│   ├── tasks/               email_tasks, priority_tasks
│   ├── utils/                constants, exceptions, storage, wards
│   ├── model.py               User, Department, Complaint, ComplaintUpdate, ComplaintImage,
│   │                           Notification, Rating, ChatSession
│   └── main.py
├── alembic/                     every applied migration
├── scripts/                     create_admin.py
├── Testing/                     the real test suite
├── location_validation.py, complaint_assign_schema.py, complaint_internal_notes_schema.py,
│   api-doc.yaml, implementation.md          historical design docs, see below
├── requirements.txt
└── .env.example
```

### Historical design docs

These used to sit loose at the repo root, they've been moved into `Backend/` since that's what they describe. Not imported by anything running.

| File | Described | Real thing now |
|---|---|---|
| `complaint_assign_schema.py` | Assignment endpoint shape | `PATCH /complaints/{id}/assign` |
| `complaint_internal_notes_schema.py` | Internal notes shape | `POST`/`GET /complaints/{id}/updates` |
| `location_validation.py` | Location validation rules | `Backend/app/schemas/complaint.py`, same VAL_001/VAL_002 codes |
| `api-doc.yaml` | Draft OpenAPI contract | Mostly superseded, real contract is `/docs` on a running server |
| `implementation.md` | Early module roadmap | Superseded by the status section below |

### Database

Eight tables: Users, Departments, Complaints, Complaint Updates, Complaint Images, Notifications, Ratings, Chat Sessions. Complaints also carries a `complaint_number` (sequential, DB-sequence-backed) alongside its real UUID id, purely for the short `NGK-000123` reference shown in the UI.

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
    COMPLAINTS ||--o{ COMPLAINT_IMAGES : attachments
    COMPLAINTS ||--|| RATINGS : rating
    COMPLAINTS ||--o{ NOTIFICATIONS : triggers
    COMPLAINTS ||--o{ CHAT_SESSIONS : discussed
```

Every user is `citizen`, `staff`, or `admin`, exactly one admin at a time. `notification_email_enabled` on `users` is the only thing `POST /notifications/preferences` controls, in-app notifications themselves are never optional.

### How auth works underneath

`auth_service.py` holds the business logic, framework agnostic. `security.py` handles password hashing and JWT. `otp_service.py` hashes and stores OTPs in Redis with a matching expiry. `token_blacklist_service.py` handles logout revocation. `rate_limit_service.py` is a general Redis limiter for forgot-password, resend-OTP, and OTP verification attempts. Every failure raises a specific exception, converted to the standard error shape by `exception_handlers.py`.

Passwords are bcrypt hashed, never logged. Access and refresh tokens carry a distinguishing claim and a unique id for real server-side logout. `require_roles` is the single reusable RBAC dependency, tested from an attacker's perspective in `test_rbac_security.py` (forged signatures, tampered payloads, expired tokens).

Staff and admin accounts can't be created through registration at all, ever. The one admin is created once via `scripts/create_admin.py`, which refuses to run again once an admin exists. That admin is the only account that can create staff, via `POST /admin/users`, which has no role field, it can only ever create staff.

### Notifications, feedback, and Celery

A notification is created synchronously, same request and transaction, on approve/reject/start/resolve (notifies the citizen), assign (notifies staff), and citizen-confirmed close whether direct or via feedback (notifies staff). High-risk complaints notify every admin instead. No Celery involved.

A citizen leaves exactly one rating per complaint, 1 to 5 stars plus optional text, only while resolved. Submitting it closes the complaint in the same call, reusing the standalone close transition, so it triggers the same staff notification.

Celery sends verification/reset email asynchronously, and Beat runs a nightly 2 AM IST priority rescore. That's all it does today, scheduled auto-close and PDF reports are planned, not built.

### Where the project actually stands

**Done and tested, backend and frontend:** the full auth flow, admin bootstrap, staff creation, RBAC, the complete complaint lifecycle including citizen delete and a staff-uploaded resolution photo, attachment upload and viewing, complaint history, automatic notifications on every transition plus a live unread badge/reminder, role-scoped analytics (including the redesigned staff performance page), profile editing and password reset, feedback with auto-close, department management and department-filtered staff assignment, deterministic category-to-department routing, the chatbot filing real complaints (with photos, and now linking straight to the filed complaint) and answering questions. Covered by a real passing test suite and verified by hand end to end in the browser.

**Done and tested on the backend, no frontend page yet:** deleting an individual attachment, ward/category filtering (`GET /complaints/ward/{id}`, `GET /complaints/category/{category}`, the admin dashboard's own category filter is a client-side filter over the generic list, not these), feedback summary and per-officer aggregation.

**Still sample data on the frontend:** the general feedback form (no matching backend endpoint exists for it, see above).

**Planned, not started:** scheduled auto-closing of stale resolved complaints, a broader analytics dashboard, Docker/CI deployment setup, a dedicated security audit before any real launch.

### Detailed changelog

**Staff analytics redesigned:** the "My Performance" page's old category-breakdown bar chart was replaced with a workload overview, a resolution-rate ring, and a work-status breakdown.

**Chatbot links straight to the filed complaint:** filing a complaint through Nagrik Saathi now shows a "View Complaint" link right on the confirmation card, instead of leaving you to go find it yourself.

**Admin dashboard redesigned, with pagination:** a visual overhaul of the admin complaint-management screen (new hero/live-snapshot layout, filter toolbar, per-row priority/officer detail), plus proper pagination instead of dumping every complaint into one long table.

**Resolution-rating page redesigned:** `RateReview.vue` now matches the rest of the app's visual language instead of looking like a leftover prototype.

**Staff can attach a resolution photo:** once a complaint is resolved, staff can upload a photo as proof, visible to the citizen on the complaint detail page. Reuses the existing attachment upload endpoint with `purpose: resolution_proof` rather than a new endpoint.

**Department management is real, not planned:** admins can create/list/update/delete departments (`POST`/`GET /admin/departments`, `PATCH`/`DELETE /admin/departments/{id}`) and reassign a staff member's department (`PATCH /admin/users/{id}/department`), from a fixed set of BMC departments. Complaint routing to a department is now deterministic (category to department lookup) instead of going through an LLM call, and staff assignment is filtered to officers in the complaint's own department.

**Groq model swap:** `llama-3.3-70b-versatile` was decommissioned upstream, the chatbot and priority scoring now use the current Groq model instead.

**Redesign and real submit form:** the whole app got a visual redesign (Leaflet map for picking a complaint's location, new layouts throughout). `SubmitComplaint.vue` used to be a disconnected prototype with a fake stub submit and a made-up category list, it's now wired to the real backend (`createComplaint`, `uploadAttachment`, `getWards`), with the map defaulting to Mumbai instead of New Delhi.

**Attachments visible to staff/admin:** photos a citizen attaches to a complaint now show up on the staff and admin views too, not just the citizen's own.

**Chatbot photo uploads fixed:** a photo attached through Nagrik Saathi could silently fail to upload with no error and no way to retry, which is why it sometimes never showed up on the staff/admin side. Now a failed upload surfaces an error and stays attached for retry instead of vanishing. You can also send a photo on its own now, without typing anything first.

**Citizens can delete their own complaint:** while it's still "submitted" (before any officer has approved it), a citizen can now delete it outright, from the complaint detail page or `DELETE /complaints/{id}`. Once it's been approved, withdraw is the option instead.

**Notification reminders:** a red badge on the navbar bell shows the live unread count, and a dismissible banner on every dashboard (citizen, staff, admin) reminds you when there's something unread. The backend for this already existed, it just had no UI surface before.

**Admin dashboard loads faster:** it used to fetch every page of complaints one at a time in sequence. Now it fetches the first page, then every remaining page in parallel, no more 100-complaint cap either.

**Admin can reject complaints:** the Reject action existed on the backend but nothing in the UI called it, only Approve did. There's now a Reject button next to Approve for any "submitted" complaint, prompting for a reason.

**Short complaint reference numbers:** every complaint now has a sequential number (`NGK-000123`) shown everywhere instead of the raw UUID, backed by a real DB sequence so it's assigned atomically. The UUID is still the real id for URLs and API calls, this is purely for display.

### Try the full lifecycle yourself, via the API

1. **Citizen:** file a complaint through Nagrik Saathi, or `POST /complaints` directly.
2. **Admin:** `PATCH /complaints/{id}/approve`, then `PATCH /complaints/{id}/assign`.
3. **Staff:** `PATCH /complaints/{id}/start`, then `PATCH /complaints/{id}/resolve`.
4. **Citizen:** check `GET /notifications`, one entry per step above.
5. **Citizen:** `POST /complaints/{id}/feedback` with a score 1 to 5, this auto-closes the complaint.

Every call is real, hits the real database, nothing here is faked for a demo.

```bash
cd Backend && pytest        # the real test suite, 30+ minutes, real DB and real AI calls, no mocks
```

## How we work as a team

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
# work, commit in small chunks
git push -u origin feature/your-feature-name
# open a pull request into develop
```

Nothing merges directly into `main` without a reviewed pull request. Before opening a PR: code runs, no hardcoded secrets, tests pass, new dependencies are in `requirements.txt`. Schema changes need a real Alembic migration, generated with `alembic revision --autogenerate -m "..."` and reviewed by hand.

### The team

| Name | Owns |
|---|---|
| Amit Kumar Pandey | Backend architecture, auth, complaint APIs, database |
| Akshit | AI engine, priority prediction, RAG chatbot |
| Ravisha | Testing, QA, complaint schema design, docs |
| Lakshay Bansal | Frontend, Vue pages, routing, auth store |
| Arubhi Bansal | Scrum master, frontend support |

</details>

---

## License

Academic and educational purposes only, part of IIT Madras's Software Engineering coursework. All rights remain with the project's contributors unless stated otherwise.
