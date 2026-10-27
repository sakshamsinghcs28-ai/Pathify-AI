import uuid
from typing import Optional
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class SkillGapAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skill_gap_assessments"
    __table_args__ = (CheckConstraint("readiness_score BETWEEN 0 AND 100", name="ck_assessment_readiness"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("career_roles.id", ondelete="RESTRICT"), nullable=False)
    readiness_score: Mapped[float] = mapped_column(nullable=False, default=0)
    breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    user: Mapped["User"] = relationship(back_populates="assessments")
    role: Mapped["CareerRole"] = relationship(back_populates="assessments")

class Roadmap(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roadmaps"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("career_roles.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)

    milestones: Mapped[list["RoadmapMilestone"]] = relationship(back_populates="roadmap", cascade="all, delete-orphan")
    user: Mapped["User"] = relationship(back_populates="roadmaps")
    role: Mapped["CareerRole"] = relationship(back_populates="roadmaps")

class RoadmapMilestone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roadmap_milestones"
    __table_args__ = (UniqueConstraint("roadmap_id", "sequence_order"),)

    roadmap_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    roadmap: Mapped["Roadmap"] = relationship(back_populates="milestones")
    tasks: Mapped[list["RoadmapTask"]] = relationship(back_populates="milestone", cascade="all, delete-orphan")

class RoadmapTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roadmap_tasks"
    __table_args__ = (UniqueConstraint("milestone_id", "sequence_order"),)

    milestone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roadmap_milestones.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_hours: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    milestone: Mapped["RoadmapMilestone"] = relationship(back_populates="tasks")
    resource_mappings: Mapped[list["TaskResourceMapping"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    progress_records: Mapped[list["UserTaskProgress"]] = relationship(back_populates="task", cascade="all, delete-orphan")
