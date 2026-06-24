<div align="center">

# 🏛️ NAGRIK AI

### AI-Powered Civic Complaint Management Platform

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)

**Team 059** · IIT Madras Software Engineering · 2026

---

`feature/db-setup` — Database models, schema, and setup

</div>

---

## What's in this branch

This branch contains the **complete database layer** for NAGRIK AI — 6 tables built with SQLAlchemy ORM, tested and verified against a real PostgreSQL database.

### Files

| File | What It Does |
|------|-------------|
| `Backend/app/model.py` | All 6 SQLAlchemy table definitions in one file |
| `Backend/app/database.py` | Async engine, session factory, and `get_db()` dependency |
| `Backend/app/config.py` | Loads settings from `.env` using pydantic-settings |
| `Backend/app/main.py` | Minimal FastAPI app with health check |
| `Backend/test_db.py` | Script to create all tables and verify they exist |
| `Backend/requirements.txt` | All Python dependencies with pinned versions |
| `Backend/.env.example` | Template for environment variables |

---

## Database Schema — 6 Tables

```mermaid
erDiagram
    USERS ||--o{ COMPLAINTS : "files (citizen_id)"
    USERS ||--o{ COMPLAINTS : "handles (assigned_to)"
    USERS ||--o{ COMPLAINT_UPDATES : "logs (updated_by)"
    USERS ||--o{ NOTIFICATIONS : "receives"
    USERS ||--o{ RATINGS : "gives"
    USERS ||--o{ CHAT_SESSIONS : "chats"
    COMPLAINTS ||--o{ COMPLAINT_UPDATES : "has history"
    COMPLAINTS ||--o{ NOTIFICATIONS : "triggers"
    COMPLAINTS ||--|| RATINGS : "gets rated"
    COMPLAINTS ||--o{ CHAT_SESSIONS : "discussed in"

    USERS {
        uuid id PK
        string phone UK
        string name
        string email
        string role
        string password
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    COMPLAINTS {
        uuid id PK
        uuid citizen_id FK
        uuid assigned_to FK
        string title
        text description
        string category
        string status
        int priority_score
        string location_text
        text reject_reason
        timestamp created_at
        timestamp updated_at
    }

    COMPLAINT_UPDATES {
        uuid id PK
        uuid complaint_id FK
        uuid updated_by FK
        string old_status
        string new_status
        text notes
        timestamp created_at
    }

    NOTIFICATIONS {
        uuid id PK
        uuid user_id FK
        uuid complaint_id FK
        string type
        string title
        text message
        boolean is_read
        timestamp created_at
    }

    RATINGS {
        uuid id PK
        uuid complaint_id FK
        uuid citizen_id FK
        int score
        text feedback
        timestamp created_at
    }

    CHAT_SESSIONS {
        uuid id PK
        string session_id
        uuid user_id FK
        uuid complaint_id FK
        string role
        text message
        jsonb retrieved_docs
        timestamp created_at
    }
```

### What each table is for

| Table | Purpose |
|-------|---------|
| **users** | All users — citizens, staff, and admins. `role` column controls access. |
| **complaints** | Every complaint filed. Two FKs to users: `citizen_id` (who filed) and `assigned_to` (who fixes). |
| **complaint_updates** | Audit log. Every status change is recorded here — never deleted. |
| **notifications** | Alerts for citizens and staff when complaint status changes. |
| **ratings** | Citizen rates resolution quality (1–5). One rating per complaint. |
| **chat_sessions** | RAG chatbot message history. Stores both user and assistant messages. |

---

## Setup Guide

### Prerequisites

- **PostgreSQL 14+** installed and running
- **Python 3.9+**

### Step 1 — Clone and switch to this branch

```bash
git clone https://github.com/24f2000777/MAY2026-Team-059.git
cd MAY2026-Team-059
git checkout feature/db-setup
```

### Step 2 — Create virtual environment and install packages

```bash
cd Backend
python -m venv venv
source venv/bin/activate          # Mac/Linux
# venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### Step 3 — Create the PostgreSQL database

```bash
psql -h 127.0.0.1 -U postgres -d postgres
```

When prompted, enter your postgres password. Then:

```sql
CREATE DATABASE nagrik_ai;
\q
```

### Step 4 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@127.0.0.1:5432/nagrik_ai
SYNC_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@127.0.0.1:5432/nagrik_ai
SECRET_KEY=any-random-string-minimum-32-characters
GROQ_API_KEY=get-from-console.groq.com
```

### Step 5 — Create all tables

```bash
python test_db.py
```

Expected output:

```
Creating tables...

Found 6 tables:
  - chat_sessions
  - complaint_updates
  - complaints
  - notifications
  - ratings
  - users
```

### Step 6 — Verify in psql (optional)

```bash
psql -h 127.0.0.1 -U postgres -d nagrik_ai -c "\dt"
```

```
 Schema |       Name        | Type  |  Owner
--------+-------------------+-------+----------
 public | chat_sessions     | table | postgres
 public | complaint_updates | table | postgres
 public | complaints        | table | postgres
 public | notifications     | table | postgres
 public | ratings           | table | postgres
 public | users             | table | postgres
```

### Step 7 — Run the server

```bash
uvicorn app.main:app --reload
```

Visit **http://localhost:8000/health** — you should see `{"status": "ok"}`.

---

## Complaint State Machine

These transitions will be enforced in the API layer (next branch). Documented here for reference.

```mermaid
stateDiagram-v2
    [*] --> Submitted : Citizen files complaint
    Submitted --> Assigned : Admin assigns to staff
    Submitted --> Rejected : Admin rejects
    Assigned --> In_Progress : Staff starts work
    Assigned --> Rejected : Admin rejects
    In_Progress --> Resolved : Staff resolves
    Resolved --> Closed : Citizen confirms / Auto 7 days
```

---

## What's Next

This branch will be merged into `develop` via PR. The next branches to be built:

- `feature/api-auth` — authentication endpoints (Amit)
- `feature/api-complaints` — complaint CRUD endpoints (Amit)
- `feature/ai-engine` — ML priority scoring model (Akshit)
- `feature/rag-chatbot` — RAG chatbot (Akshit)
- `feature/tests` — pytest test suite (Ravisha)

---

<div align="center">

**NAGRIK AI** · Team 059 · IIT Madras SE 2026

</div>
