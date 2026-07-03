# NAGRIK AI Backend Learning Notes

## Git, PostgreSQL, FastAPI Database Layer and Team Workflow

### Amit Kumar Pandey – Team 059

---

# Chapter 1: Big Picture of NAGRIK AI

NAGRIK AI is not just a Python project.

It is a layered software system.

```text
Citizen
    ↓
React Frontend
    ↓
FastAPI Backend
    ↓
Authentication Layer
    ↓
Business Logic
    ↓
SQLAlchemy
    ↓
PostgreSQL
```

Your responsibility:

```text
feature/api-auth
```

This means:

* Registration
* Login
* JWT Tokens
* Authentication
* Authorization
* Role-based Access

---

# Chapter 2: Git and Team Workflow

## Why branches exist

Suppose 4 students work on the same project.

Without branches:

```text
Everyone edits main branch.
```

Result:

* code conflicts
* overwritten files
* broken application

Therefore:

```text
main
│
develop
│
├── feature/db-setup
├── feature/api-auth
├── feature/ai-engine
└── feature/tests
```

---

# main branch

Production code.

Never directly commit.

---

# develop branch

Team integration branch.

All features merge here.

---

# feature branch

Individual developer branch.

Example:

```text
feature/api-auth
```

Only authentication work belongs here.

---

# Your workflow

```bash
git checkout develop
git pull origin develop
git checkout -b feature/api-auth
```

---

# Mental Model

```text
main
    │
develop
    │
    └── feature/api-auth
```

You build here.

After review:

```text
feature/api-auth
         ↓
develop
```

Later:

```text
develop
    ↓
main
```

---

# Chapter 3: What is origin?

```bash
git remote -v
```

Output:

```text
origin https://github.com/... (fetch)
origin https://github.com/... (push)
```

Origin means:

> GitHub repository.

---

# Fetch

Download.

```bash
git pull origin develop
```

---

# Push

Upload.

```bash
git push origin feature/api-auth
```

---

# Mental Model

```text
GitHub
    ▲
    │ push
origin
    │ fetch
    ▼

Your Laptop
```

---

# Chapter 4: Why git checkout develop?

```bash
git checkout develop
```

Move to:

```text
develop branch
```

---

# Why git pull?

Your teammate may have merged:

```text
feature/db-setup
        ↓
develop
```

Your local machine may not know this.

```bash
git pull origin develop
```

downloads latest code.

---

# Chapter 5: PostgreSQL Clusters

Your machine:

```text
17 main 5433 down
18 main 5432 online
```

Cluster means:

* database server
* configuration
* users
* databases

You currently use:

```text
PostgreSQL 18
Port 5432
```

---

# Chapter 6: Database Driver

FastAPI cannot directly talk to PostgreSQL.

```text
FastAPI
    ↓
Driver
    ↓
PostgreSQL
```

Driver = translator.

---

# psycopg2

Traditional PostgreSQL driver.

```python
db.execute()
```

Program waits.

---

# asyncpg

Asynchronous PostgreSQL driver.

```python
await db.execute()
```

Program can do other work while waiting.

---

# Why Two URLs?

```env
DATABASE_URL=
SYNC_DATABASE_URL=
```

---

## DATABASE_URL

```text
asyncpg
```

Used by:

* FastAPI
* Login APIs
* Complaint APIs
* JWT APIs

---

## SYNC_DATABASE_URL

```text
psycopg2
```

Used by:

* test_db.py
* create_all()
* scripts
* migrations

---

# Mental Model

```text
FastAPI
    ↓
asyncpg
    ↓
PostgreSQL

test_db.py
    ↓
psycopg2
    ↓
PostgreSQL
```

---

# Chapter 7: Why FastAPI Uses async?

Suppose 100 users login.

Synchronous:

```text
User 1 waits.
User 2 waits.
User 3 waits.
```

Asynchronous:

```text
User 1 waiting.
User 2 executing.
User 3 executing.
```

Server utilization improves.

---

# Chapter 8: Virtual Environment

Without venv:

```text
Entire Ubuntu uses one Python.
```

Problem:

```text
Project A:
SQLAlchemy 2

Project B:
SQLAlchemy 1
```

Conflict.

---

Solution:

```bash
python -m venv venv
```

Project gets isolated environment.

---

# Chapter 9: requirements.txt

Contains:

```text
fastapi
sqlalchemy
asyncpg
psycopg2
```

Ensures every developer installs identical versions.

---

# Chapter 10: .env

Bad:

```python
password = "amit123"
```

Good:

```env
DATABASE_URL=...
SECRET_KEY=...
```

---

# Why?

Each developer can use different passwords.

---

# .env.example

Template:

```env
DATABASE_URL=
SECRET_KEY=
```

---

# .env

Personal.

Never upload to GitHub.

---

# Chapter 11: config.py

Purpose:

Read environment variables.

Example:

```python
settings.DATABASE_URL
```

Without config.py:

```python
DATABASE_URL = "hardcoded"
```

---

# Chapter 12: Base

Usually:

```python
Base = declarative_base()
```

Base is parent class.

Example:

```python
class User(Base):
```

```python
class Complaint(Base):
```

---

# Chapter 13: SQLAlchemy Models

Models describe tables.

Example:

```python
class User(Base):
```

represents:

```text
users table
```

---

# Chapter 14: create_all()

```python
Base.metadata.create_all()
```

SQLAlchemy says:

```text
User → create users
Complaint → create complaints
Rating → create ratings
```

---

# Chapter 15: Why Import Models?

```python
from app.model import User
```

Without importing:

```text
SQLAlchemy does not know table exists.
```

No table gets created.

---

# Chapter 16: test_db.py

Purpose:

1. Connect database.
2. Create tables.
3. Verify tables.

---

```python
create_engine()
```

Connect.

---

```python
create_all()
```

Create tables.

---

```python
SELECT table_name
```

Verify.

---

# Chapter 17: main.py

Minimal FastAPI app.

Example:

```python
app = FastAPI()

@app.get("/health")
async def health():
    return {"status":"ok"}
```

---

# Why /health?

Before authentication.

Before complaints.

Before AI.

Verify:

```text
Server alive?
```

---

# Chapter 18: Database Schema

users

Stores:

* citizen
* officer
* admin

---

complaints

Stores:

* title
* description
* status
* category

---

complaint_updates

Audit history.

Never deleted.

---

notifications

Messages.

---

ratings

Citizen feedback.

---

chat_sessions

AI chatbot history.

---

# Chapter 19: Authentication Architecture

Your future work.

```text
User
    ↓
POST /auth/login
    ↓
FastAPI
    ↓
Database
    ↓
Password Verification
    ↓
JWT Token
    ↓
Response
```

---

# Registration Flow

```text
Citizen
    ↓
POST /auth/register
    ↓
Hash Password
    ↓
Save User
```

---

# Login Flow

```text
Email
Password
    ↓
Database Lookup
    ↓
Verify Password
    ↓
Generate JWT
```

---

# Protected Route

```text
Browser
    ↓
Authorization: Bearer TOKEN
    ↓
FastAPI
    ↓
Decode JWT
    ↓
Identify User
```

---

# Role-Based Access

Citizen:

```text
Create Complaint
```

Officer:

```text
Resolve Complaint
```

Admin:

```text
Assign Complaint
```

---

# Chapter 20: Your Immediate Roadmap

Step 1:

```bash
Create nagrik_ai database
```

Step 2:

```bash
Create .env
```

Step 3:

```bash
Create virtual environment
```

Step 4:

```bash
pip install -r requirements.txt
```

Step 5:

```bash
python test_db.py
```

Step 6:

```bash
uvicorn app.main:app --reload
```

Step 7:

Visit:

```text
http://localhost:8000/health
```

---

# Future Learning Topics

* AsyncSession
* create_async_engine
* Depends()
* get_db()
* Pydantic schemas
* Password hashing
* JWT
* OAuth2PasswordBearer
* Refresh Tokens
* Role Based Access Control
* Alembic migrations
* Repository pattern

---

# Chapter 21: Are We Using Two Databases?

This is one of the biggest confusions beginners have.

When they see:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/nagrik_ai

SYNC_DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/nagrik_ai
```

they often think:

```text
Database 1
Database 2
```

This is WRONG.

---

# We Have Only ONE Database

Look carefully:

```text
localhost:5432/nagrik_ai
```

Both URLs point to:

* same server
* same port
* same database
* same tables

The only thing that changes is:

```text
asyncpg
psycopg2
```

---

# Real Example

Suppose your PostgreSQL contains:

```text
nagrik_ai
    |
    ├── users
    ├── complaints
    ├── ratings
    └── notifications
```

Both URLs connect to exactly this database.

---

# Visual Picture

```text
            PostgreSQL

          Database:
            nagrik_ai

      ┌─────────┴─────────┐
      │                   │

asyncpg driver      psycopg2 driver

      │                   │

FastAPI APIs         test_db.py
Authentication       create_all()
Complaint APIs       utility scripts
```

---

# Think About a Building

Suppose there is one municipal office.

There are two entrances.

```text
             Municipal Office

           (nagrik_ai database)

               /        \
              /          \

     Main Gate          Service Gate

      asyncpg            psycopg2
```

Both people enter the same building.

They simply use different entrances.

---

# Why Not One Driver Everywhere?

Technically possible.

You could write everything using:

```text
asyncpg
```

or everything using:

```text
psycopg2
```

But this creates problems.

---

# Problem 1: FastAPI Wants Async

FastAPI routes:

```python
async def login():
```

want:

```python
await db.execute(...)
```

which requires:

```text
asyncpg
```

---

# Problem 2: create_all() Is Easier With Sync

This:

```python
Base.metadata.create_all()
```

was originally designed for synchronous engines.

So:

```text
psycopg2
```

is much simpler.

---

# Actual Connections in This Project

When you run:

```bash
python test_db.py
```

this happens:

```text
test_db.py
      ↓
SYNC_DATABASE_URL
      ↓
psycopg2
      ↓
nagrik_ai
```

---

When the server starts:

```bash
uvicorn app.main:app --reload
```

this happens:

```text
FastAPI
      ↓
DATABASE_URL
      ↓
asyncpg
      ↓
nagrik_ai
```

---

# Are Tables Shared?

YES.

Suppose:

```bash
python test_db.py
```

creates:

```text
users
complaints
ratings
```

When FastAPI starts:

```text
FastAPI
     ↓
asyncpg
     ↓
users table
```

It sees exactly the same tables.

There are not:

```text
users_async
users_sync
```

There is only:

```text
users
```

---

# What Happens During Login?

```text
POST /auth/login
        ↓
FastAPI
        ↓
asyncpg
        ↓
users table
        ↓
check password
        ↓
return JWT
```

---

# What Happens During test_db.py?

```text
test_db.py
        ↓
psycopg2
        ↓
users table
        ↓
create table if missing
```

---

# Mental Model

Think of:

```text
DATABASE_URL
```

as:

```text
Application Connection
```

and:

```text
SYNC_DATABASE_URL
```

as:

```text
Administrative Connection
```

---

# Final Architecture

```text
                    PostgreSQL

                Database:
                 nagrik_ai

         ┌────────────┴────────────┐

         │                         │

DATABASE_URL               SYNC_DATABASE_URL

         │                         │

      asyncpg                 psycopg2

         │                         │

    FastAPI APIs             test_db.py

    Authentication           create_all()

    Complaints               scripts

    JWT                      migrations
```

---

# Important Conclusion

This project uses:

```text
ONE PostgreSQL server
ONE PostgreSQL database
ONE set of tables
TWO database drivers
TWO connection URLs
```

The URLs differ because the application and the utility scripts have different requirements, not because there are multiple databases.

