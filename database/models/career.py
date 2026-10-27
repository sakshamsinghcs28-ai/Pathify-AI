import uuid
from typing import Optional
from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class CareerRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_roles"
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    industry: Mapped[Optional[str]] = mapped_column(String(120))

    skill_requirements: Mapped[list["CareerSkillRequirement"]] = relationship(back_populates="role", cascade="all, delete-orphan")
    roadmaps: Mapped[list["Roadmap"]] = relationship(back_populates="role")
    assessments: Mapped[list["SkillGapAssessment"]] = relationship(back_populates="role")

class CareerSkillRequirement(Base):
    __tablename__ = "career_skill_requirements"
    __table_args__ = (
        UniqueConstraint("role_id", "skill_id"),
        CheckConstraint("required_level BETWEEN 1 AND 5", name="ck_role_skill_required_level"),
    )
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("career_roles.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), primary_key=True)
    required_level: Mapped[int] = mapped_column(default=3, nullable=False)
    importance: Mapped[str] = mapped_column(String(20), default="required", nullable=False)

    role: Mapped["CareerRole"] = relationship(back_populates="skill_requirements")
    skill: Mapped["Skill"] = relationship(back_populates="career_requirements")
