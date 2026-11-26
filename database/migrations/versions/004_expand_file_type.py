"""Expand file_type column length in resume_analyses

Revision ID: 004_expand_file_type
Revises: 003_resume_analysis
Create Date: 2026-11-24 19:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_expand_file_type'
down_revision: Union[str, None] = '003_resume_analysis'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'resume_analyses',
        'file_type',
        existing_type=sa.String(length=50),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'resume_analyses',
        'file_type',
        existing_type=sa.String(length=255),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
