import uuid
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="student", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped[Optional["UserProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    skills: Mapped[list["UserSkill"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    roadmaps: Mapped[list["Roadmap"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    assessments: Mapped[list["SkillGapAssessment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    task_progress: Mapped[list["UserTaskProgress"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    ai_logs: Mapped[list["AIGenerationLog"]] = relationship(back_populates="user")

class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(160))
    education: Mapped[Optional[str]] = mapped_column(String(255))
    experience_level: Mapped[Optional[str]] = mapped_column(String(80))
    weekly_hours_budget: Mapped[Optional[int]]
    budget_notes: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="profile")
