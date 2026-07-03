# Run this to create all 6 tables and verify they exist
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.database import Base
from app.model import (
    User,
    Complaint,
    ComplaintUpdate,
    Notification,
    Rating,
    ChatSession,
)

engine = create_engine(settings.SYNC_DATABASE_URL)

print("Creating tables...")
Base.metadata.create_all(engine)

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    ))
    tables = [row[0] for row in result]

print(f"\nFound {len(tables)} tables:")
for t in tables:
    print(f"  - {t}")
