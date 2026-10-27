import uuid
from typing import Optional
from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="technical", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    prerequisites: Mapped[list["SkillPrerequisite"]] = relationship(
        foreign_keys="SkillPrerequisite.skill_id",
        back_populates="skill",
        cascade="all, delete-orphan",
    )
    career_requirements: Mapped[list["CareerSkillRequirement"]] = relationship(back_populates="skill")
    user_skills: Mapped[list["UserSkill"]] = relationship(back_populates="skill")

class SkillPrerequisite(Base):
    __tablename__ = "skill_prerequisites"
    __table_args__ = (UniqueConstraint("skill_id", "prerequisite_skill_id"),)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    prerequisite_skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), primary_key=True)

    skill: Mapped["Skill"] = relationship(foreign_keys=[skill_id], back_populates="prerequisites")
    prerequisite_skill: Mapped["Skill"] = relationship(foreign_keys=[prerequisite_skill_id])

class UserSkill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_skills"
    __table_args__ = (
        CheckConstraint("proficiency_level BETWEEN 1 AND 5", name="ck_user_skill_proficiency"),
        UniqueConstraint("user_id", "skill_id"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False, index=True)
    proficiency_level: Mapped[int] = mapped_column(default=1, nullable=False)
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="user_skills")
