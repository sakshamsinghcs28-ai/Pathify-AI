import uuid
from typing import Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class AIGenerationLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_generation_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    feature: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_summary: Mapped[Optional[str]] = mapped_column(Text)
    response_summary: Mapped[Optional[str]] = mapped_column(Text)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    user: Mapped[Optional["User"]] = relationship(back_populates="ai_logs")
