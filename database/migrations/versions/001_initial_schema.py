"""Initial schema for Pathify-AI database

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-26 23:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # --- Table: career_roles ---
    op.create_table(
        'career_roles',
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(length=120), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_career_roles_slug', 'career_roles', ['slug'], unique=True)

    # --- Table: learning_resources ---
    op.create_table(
        'learning_resources',
        sa.Column('title', sa.String(length=240), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('resource_type', sa.String(length=40), nullable=False),
        sa.Column('provider', sa.String(length=120), nullable=True),
        sa.Column('difficulty', sa.String(length=40), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- Table: skills ---
    op.create_table(
        'skills',
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('category', sa.String(length=80), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skills_slug', 'skills', ['slug'], unique=True)

    # --- Table: users ---
    op.create_table(
        'users',
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # --- Table: ai_generation_logs ---
    op.create_table(
        'ai_generation_logs',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('feature', sa.String(length=80), nullable=False),
        sa.Column('prompt_summary', sa.Text(), nullable=True),
        sa.Column('response_summary', sa.Text(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_ai_generation_logs_user_id', 'ai_generation_logs', ['user_id'], unique=False)

    # --- Table: career_skill_requirements ---
    op.create_table(
        'career_skill_requirements',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('required_level', sa.Integer(), nullable=False),
        sa.Column('importance', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('role_id', 'skill_id'),
        sa.CheckConstraint('required_level BETWEEN 1 AND 5', name='ck_role_skill_required_level'),
        sa.ForeignKeyConstraint(['role_id'], ['career_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('role_id', 'skill_id'),
    )

    # --- Table: roadmaps ---
    op.create_table(
        'roadmaps',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['role_id'], ['career_roles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_roadmaps_user_id', 'roadmaps', ['user_id'], unique=False)

    # --- Table: skill_gap_assessments ---
    op.create_table(
        'skill_gap_assessments',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('readiness_score', sa.Float(), nullable=False),
        sa.Column('breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('readiness_score BETWEEN 0 AND 100', name='ck_assessment_readiness'),
        sa.ForeignKeyConstraint(['role_id'], ['career_roles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_skill_gap_assessments_user_id', 'skill_gap_assessments', ['user_id'], unique=False)

    # --- Table: skill_prerequisites ---
    op.create_table(
        'skill_prerequisites',
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('prerequisite_skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('skill_id', 'prerequisite_skill_id'),
        sa.ForeignKeyConstraint(['prerequisite_skill_id'], ['skills.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('skill_id', 'prerequisite_skill_id'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
    )

    # --- Table: user_profiles ---
    op.create_table(
        'user_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.String(length=160), nullable=True),
        sa.Column('education', sa.String(length=255), nullable=True),
        sa.Column('experience_level', sa.String(length=80), nullable=True),
        sa.Column('weekly_hours_budget', sa.Integer(), nullable=True),
        sa.Column('budget_notes', sa.Text(), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id'),
    )

    # --- Table: user_skills ---
    op.create_table(
        'user_skills',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('proficiency_level', sa.Integer(), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint('proficiency_level BETWEEN 1 AND 5', name='ck_user_skill_proficiency'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('user_id', 'skill_id'),
    )
    op.create_index('ix_user_skills_skill_id', 'user_skills', ['skill_id'], unique=False)
    op.create_index('ix_user_skills_user_id', 'user_skills', ['user_id'], unique=False)

    # --- Table: roadmap_milestones ---
    op.create_table(
        'roadmap_milestones',
        sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('roadmap_id', 'sequence_order'),
        sa.ForeignKeyConstraint(['roadmap_id'], ['roadmaps.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_roadmap_milestones_roadmap_id', 'roadmap_milestones', ['roadmap_id'], unique=False)

    # --- Table: roadmap_tasks ---
    op.create_table(
        'roadmap_tasks',
        sa.Column('milestone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('estimated_hours', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['milestone_id'], ['roadmap_milestones.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('milestone_id', 'sequence_order'),
    )
    op.create_index('ix_roadmap_tasks_milestone_id', 'roadmap_tasks', ['milestone_id'], unique=False)

    # --- Table: task_resource_mappings ---
    op.create_table(
        'task_resource_mappings',
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('task_id', 'resource_id'),
        sa.UniqueConstraint('task_id', 'resource_id'),
        sa.ForeignKeyConstraint(['task_id'], ['roadmap_tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resource_id'], ['learning_resources.id'], ondelete='CASCADE'),
    )

    # --- Table: user_task_progress ---
    op.create_table(
        'user_task_progress',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('progress_percent', sa.Integer(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['task_id'], ['roadmap_tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint('progress_percent BETWEEN 0 AND 100', name='ck_task_progress_percent'),
        sa.UniqueConstraint('user_id', 'task_id'),
    )
    op.create_index('ix_user_task_progress_task_id', 'user_task_progress', ['task_id'], unique=False)
    op.create_index('ix_user_task_progress_user_id', 'user_task_progress', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_user_task_progress_task_id', table_name='user_task_progress')
    op.drop_index('ix_user_task_progress_user_id', table_name='user_task_progress')
    op.drop_table('user_task_progress')
    op.drop_table('task_resource_mappings')
    op.drop_index('ix_roadmap_tasks_milestone_id', table_name='roadmap_tasks')
    op.drop_table('roadmap_tasks')
    op.drop_index('ix_roadmap_milestones_roadmap_id', table_name='roadmap_milestones')
    op.drop_table('roadmap_milestones')
    op.drop_index('ix_user_skills_skill_id', table_name='user_skills')
    op.drop_index('ix_user_skills_user_id', table_name='user_skills')
    op.drop_table('user_skills')
    op.drop_table('user_profiles')
    op.drop_table('skill_prerequisites')
    op.drop_index('ix_skill_gap_assessments_user_id', table_name='skill_gap_assessments')
    op.drop_table('skill_gap_assessments')
    op.drop_index('ix_roadmaps_user_id', table_name='roadmaps')
    op.drop_table('roadmaps')
    op.drop_table('career_skill_requirements')
    op.drop_index('ix_ai_generation_logs_user_id', table_name='ai_generation_logs')
    op.drop_table('ai_generation_logs')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    op.drop_index('ix_skills_slug', table_name='skills')
    op.drop_table('skills')
    op.drop_table('learning_resources')
    op.drop_index('ix_career_roles_slug', table_name='career_roles')
    op.drop_table('career_roles')