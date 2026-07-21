# All 7 database tables for NAGRIK AI
from sqlalchemy.orm import relationship
from sqlalchemy import Text, Integer, String, Column, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


# ─── TABLE 1: USERS ────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(15), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    role = Column(String(20), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # one citizen can file many complaints
    complaints = relationship(
        "Complaint",
        foreign_keys="Complaint.citizen_id",
        backref="citizen",
        lazy=True,
    )


# ─── TABLE 2: COMPLAINTS ────────────────────────────────
class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    citizen_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(20), nullable=False)
    status = Column(String(20), default="submitted")
    priority_score = Column(Integer, default=0)
    location_text = Column(String(300), nullable=True)
    reject_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    updates = relationship(
        "ComplaintUpdate",
        backref="complaint",
        lazy=True,
        cascade="all, delete-orphan",
    )
    images = relationship(
        "ComplaintImage",
        backref="complaint",
        lazy=True,
        cascade="all, delete-orphan",
    )
    rating = relationship("Rating", backref="complaint", uselist=False)


# ─── TABLE 3: COMPLAINT_UPDATES ─────────────────────────
# audit log — every status change gets a row here
class ComplaintUpdate(Base):
    __tablename__ = "complaint_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id = Column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False
    )
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# ─── TABLE 4: COMPLAINT_IMAGES ──────────────────────────
# photos a citizen attaches to a complaint at submission time
class ComplaintImage(Base):
    __tablename__ = "complaint_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id = Column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False
    )
    image_url = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ─── TABLE 5: NOTIFICATIONS ─────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    complaint_id = Column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="SET NULL"), nullable=True
    )
    type = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


# ─── TABLE 6: RATINGS ───────────────────────────────────
# one rating per complaint (unique constraint on complaint_id)
class Rating(Base):
    __tablename__ = "ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id = Column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )
    citizen_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)  # 1 to 5
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# ─── TABLE 7: CHAT_SESSIONS ─────────────────────────────
# stores RAG chatbot messages, both user and assistant
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id"), nullable=True)
    role = Column(String(10), nullable=False)  # 'user' | 'assistant'
    message = Column(Text, nullable=False)
    retrieved_docs = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=func.now())