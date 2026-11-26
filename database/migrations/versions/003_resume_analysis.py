"""Add resume analyses table

Revision ID: 003_resume_analysis
Revises: 002_password_reset_tokens
Create Date: 2026-11-23 09:50:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_resume_analysis'
down_revision: Union[str, None] = '002_password_reset_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'resume_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('parsed_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('target_job_description', sa.Text(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('pillar_formatting_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('pillar_content_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('pillar_skills_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('pillar_experience_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('score_breakdown', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('matched_skills', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('missing_skills', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('jd_match_percentage', sa.Float(), nullable=True),
        sa.Column('improvement_recommendations', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('overall_score BETWEEN 0 AND 100', name='ck_resume_overall_score'),
        sa.ForeignKeyConstraint(['role_id'], ['career_roles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_resume_analyses_user_id', 'resume_analyses', ['user_id'], unique=False)
    op.create_index('ix_resume_analyses_role_id', 'resume_analyses', ['role_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_resume_analyses_role_id', table_name='resume_analyses')
    op.drop_index('ix_resume_analyses_user_id', table_name='resume_analyses')
    op.drop_table('resume_analyses')
