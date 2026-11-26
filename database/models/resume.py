import uuid
from typing import Optional
from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class ResumeAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resume_analyses"
    __table_args__ = (
        CheckConstraint("overall_score BETWEEN 0 AND 100", name="ck_resume_overall_score"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    target_job_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 4-Pillar Scores (0 - 100)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pillar_formatting_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pillar_content_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pillar_skills_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pillar_experience_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Detailed Analysis Findings
    score_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    matched_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    missing_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    jd_match_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    improvement_recommendations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    user: Mapped["User"] = relationship(back_populates="resumes")
    role: Mapped[Optional["CareerRole"]] = relationship()
