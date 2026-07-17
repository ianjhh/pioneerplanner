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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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