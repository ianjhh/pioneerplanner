CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS courses (
    course_id VARCHAR(10) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    department VARCHAR(50) NOT NULL,
    units INTEGER NOT NULL,
    description TEXT,
    availability TEXT[],   -- e.g. {Fall,Spring} — terms typically offered
    embedding vector(768),
    prerequisite_rule JSONB,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(course_id, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(title, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'C')
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS courses_search_idx ON courses USING GIN (search_vector);

-- prerequisite/dependency edges
CREATE TABLE IF NOT EXISTS prerequisites (
    id SERIAL PRIMARY KEY,
    target_course_id VARCHAR(10) REFERENCES courses(course_id) ON DELETE CASCADE,
    prereq_course_id VARCHAR(10) REFERENCES courses(course_id) ON DELETE CASCADE,
    logic_type VARCHAR(3) NOT NULL,        -- 'AND' or 'OR'
    minimum_grade VARCHAR(2) DEFAULT 'C',

    -- no duplicate rows
    UNIQUE(target_course_id, prereq_course_id, logic_type)
);

-- offerings table for scheduled sections
CREATE TABLE IF NOT EXISTS offerings (
    id SERIAL PRIMARY KEY,
    course_id VARCHAR(10) REFERENCES courses(course_id) ON DELETE CASCADE,
    term VARCHAR(20) NOT NULL,             -- e.g. 'Fall 2026'
    section VARCHAR(10) NOT NULL,          -- e.g. '01'
    instructor VARCHAR(100),
    time_schedule VARCHAR(100),            -- e.g. 'MoWe 10:00AM - 11:15AM'
    room VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(course_id, term, section)
);