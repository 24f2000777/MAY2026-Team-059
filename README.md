# NAGRIK AI — Civic Complaint Management Platform

Team 059 | IIT Madras Software Engineering 2026

## Setup

```bash
cd Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in real values in .env

uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for API docs.

## Project Structure

```
Backend/app/
├── main.py       — FastAPI entry point
├── config.py     — settings from .env
├── database.py   — DB engine and session
└── model.py      — all 6 SQLAlchemy tables
```
