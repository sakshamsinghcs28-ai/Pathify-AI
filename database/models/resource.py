import uuid
from typing import Optional
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class LearningResource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_resources"

    title: Mapped[str] = mapped_column(String(240), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), default="article", nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(120))
    difficulty: Mapped[Optional[str]] = mapped_column(String(40))

    task_mappings: Mapped[list["TaskResourceMapping"]] = relationship(back_populates="resource", cascade="all, delete-orphan")

class TaskResourceMapping(Base):
    __tablename__ = "task_resource_mappings"
    __table_args__ = (UniqueConstraint("task_id", "resource_id"),)

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roadmap_tasks.id", ondelete="CASCADE"), primary_key=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_resources.id", ondelete="CASCADE"), primary_key=True)

    task: Mapped["RoadmapTask"] = relationship(back_populates="resource_mappings")
    resource: Mapped["LearningResource"] = relationship(back_populates="task_mappings")
