-- vector database for course info
CREATE TABLE IF NOT EXISTS courses (
    course_id CHAR(5) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    department VARCHAR(50) NOT NULL,
    units INTEGER NOT NULL,
    description TEXT,
    embedding vector(1536), --1536 gives balance between cost efficiency and capturing complex meaning
    
    -- rules for courses
    -- example: {"any_of": [{"all_of": ["CS 101", "CS 102"]}, {"course": "Math 201", "min_grade": "B"}]}
    prerequisite_rule JSONB, 
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- course dependency table
CREATE TABLE IF NOT EXISTS course_dependencies (
    id SERIAL PRIMARY KEY,
    target_course_id CHAR(5) REFERENCES courses(course_id) ON DELETE CASCADE,
    prereq_course_id CHAR(5) REFERENCES courses(course_id) ON DELETE CASCADE,
    
    -- no duplicate rows
    UNIQUE(target_course_id, prereq_course_id)
);