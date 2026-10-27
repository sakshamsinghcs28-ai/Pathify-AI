BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001_initial_schema

CREATE TABLE career_roles (
    slug VARCHAR(120) NOT NULL, 
    title VARCHAR(160) NOT NULL, 
    description TEXT, 
    industry VARCHAR(120), 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_career_roles_slug ON career_roles (slug);

CREATE TABLE learning_resources (
    title VARCHAR(240) NOT NULL, 
    url TEXT NOT NULL, 
    resource_type VARCHAR(40) NOT NULL, 
    provider VARCHAR(120), 
    difficulty VARCHAR(40), 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE skills (
    slug VARCHAR(120) NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    category VARCHAR(80) NOT NULL, 
    description TEXT, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_skills_slug ON skills (slug);

CREATE TABLE users (
    email VARCHAR(320) NOT NULL, 
    hashed_password VARCHAR(255), 
    role VARCHAR(30) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE ai_generation_logs (
    user_id UUID, 
    feature VARCHAR(80) NOT NULL, 
    prompt_summary TEXT, 
    response_summary TEXT, 
    tokens_used INTEGER, 
    latency_ms INTEGER, 
    metadata JSONB NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_ai_generation_logs_user_id ON ai_generation_logs (user_id);

CREATE TABLE career_skill_requirements (
    role_id UUID NOT NULL, 
    skill_id UUID NOT NULL, 
    required_level INTEGER NOT NULL, 
    importance VARCHAR(20) NOT NULL, 
    PRIMARY KEY (role_id, skill_id), 
    CONSTRAINT ck_role_skill_required_level CHECK (required_level BETWEEN 1 AND 5), 
    FOREIGN KEY(role_id) REFERENCES career_roles (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT, 
    UNIQUE (role_id, skill_id)
);

CREATE TABLE roadmaps (
    user_id UUID NOT NULL, 
    role_id UUID NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(role_id) REFERENCES career_roles (id) ON DELETE RESTRICT, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_roadmaps_user_id ON roadmaps (user_id);

CREATE TABLE skill_gap_assessments (
    user_id UUID NOT NULL, 
    role_id UUID NOT NULL, 
    readiness_score FLOAT NOT NULL, 
    breakdown JSONB NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_assessment_readiness CHECK (readiness_score BETWEEN 0 AND 100), 
    FOREIGN KEY(role_id) REFERENCES career_roles (id) ON DELETE RESTRICT, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_skill_gap_assessments_user_id ON skill_gap_assessments (user_id);

CREATE TABLE skill_prerequisites (
    skill_id UUID NOT NULL, 
    prerequisite_skill_id UUID NOT NULL, 
    PRIMARY KEY (skill_id, prerequisite_skill_id), 
    FOREIGN KEY(prerequisite_skill_id) REFERENCES skills (id) ON DELETE RESTRICT, 
    UNIQUE (skill_id, prerequisite_skill_id), 
    FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

CREATE TABLE user_profiles (
    user_id UUID NOT NULL, 
    full_name VARCHAR(160), 
    education VARCHAR(255), 
    experience_level VARCHAR(80), 
    weekly_hours_budget INTEGER, 
    budget_notes TEXT, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    UNIQUE (user_id)
);

CREATE TABLE user_skills (
    user_id UUID NOT NULL, 
    skill_id UUID NOT NULL, 
    proficiency_level INTEGER NOT NULL, 
    verified BOOLEAN NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT ck_user_skill_proficiency CHECK (proficiency_level BETWEEN 1 AND 5), 
    FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT, 
    UNIQUE (user_id, skill_id)
);

CREATE INDEX ix_user_skills_skill_id ON user_skills (skill_id);

CREATE INDEX ix_user_skills_user_id ON user_skills (user_id);

CREATE TABLE roadmap_milestones (
    roadmap_id UUID NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    sequence_order INTEGER NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (roadmap_id, sequence_order), 
    FOREIGN KEY(roadmap_id) REFERENCES roadmaps (id) ON DELETE CASCADE
);

CREATE INDEX ix_roadmap_milestones_roadmap_id ON roadmap_milestones (roadmap_id);

CREATE TABLE roadmap_tasks (
    milestone_id UUID NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    description TEXT, 
    sequence_order INTEGER NOT NULL, 
    estimated_hours INTEGER NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(milestone_id) REFERENCES roadmap_milestones (id) ON DELETE CASCADE, 
    UNIQUE (milestone_id, sequence_order)
);

CREATE INDEX ix_roadmap_tasks_milestone_id ON roadmap_tasks (milestone_id);

CREATE TABLE task_resource_mappings (
    task_id UUID NOT NULL, 
    resource_id UUID NOT NULL, 
    PRIMARY KEY (task_id, resource_id), 
    UNIQUE (task_id, resource_id), 
    FOREIGN KEY(task_id) REFERENCES roadmap_tasks (id) ON DELETE CASCADE, 
    FOREIGN KEY(resource_id) REFERENCES learning_resources (id) ON DELETE CASCADE
);

CREATE TABLE user_task_progress (
    user_id UUID NOT NULL, 
    task_id UUID NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    progress_percent INTEGER NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(task_id) REFERENCES roadmap_tasks (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT ck_task_progress_percent CHECK (progress_percent BETWEEN 0 AND 100), 
    UNIQUE (user_id, task_id)
);

CREATE INDEX ix_user_task_progress_task_id ON user_task_progress (task_id);

CREATE INDEX ix_user_task_progress_user_id ON user_task_progress (user_id);

INSERT INTO alembic_version (version_num) VALUES ('001_initial_schema') RETURNING alembic_version.version_num;

COMMIT;

