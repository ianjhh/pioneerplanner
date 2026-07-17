import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from models import CourseModel
from typing import List

async def save_course_to_db(session: AsyncSession, course: CourseModel, embedding: List[float]):
    """
    Inserts or updates a course and its prerequisite graph nodes into Postgres.
    """
    # 1. UPSERT the primary course data
    # 'ON CONFLICT' ensures that if we run the scraper multiple times, it updates
    # existing course details rather than crashing on duplicate primary key errors.
    course_query = text("""
        INSERT INTO courses (course_id, title, department, units, description, availability, embedding)
        VALUES (:course_id, :title, :department, :units, :description, :availability, :embedding)
        ON CONFLICT (course_id) 
        DO UPDATE SET 
            title = EXCLUDED.title,
            department = EXCLUDED.department,
            units = EXCLUDED.units,
            description = EXCLUDED.description,
            availability = EXCLUDED.availability,
            embedding = EXCLUDED.embedding;
    """)
    
    await session.execute(
        course_query,
        {
            "course_id": course.course_id,
            "title": course.title,
            "department": course.department,
            "units": course.units,
            "description": course.description,
            "availability": course.availability, # plain Python list -> asyncpg encodes it as TEXT[]
            "embedding": str(embedding) # pgvector accepts lists formatted as strings
        }
    )
    
    # 2. Clear out old prerequisite edges for this course before writing new ones
    # This prevents ghost edges if a course requirement changes in the university catalog.
    await session.execute(
        text("DELETE FROM prerequisites WHERE target_course_id = :course_id"),
        {"course_id": course.course_id}
    )
    
    # 3. Insert the new Directed Acyclic Graph (DAG) prerequisite edges
    if course.prerequisites:
        prereq_query = text("""
            INSERT INTO prerequisites (target_course_id, prereq_course_id, logic_type, minimum_grade)
            VALUES (:target_course_id, :prereq_course_id, :logic_type, :minimum_grade)
            ON CONFLICT DO NOTHING;
        """)
        
        for group in course.prerequisites:
            for prereq_id in group.courses:
                # Each attempt runs inside its own SAVEPOINT (begin_nested). If an extracted
                # prerequisite course doesn't exist in 'courses' yet, the Foreign Key constraint
                # fails — and without a savepoint, that failure poisons the *entire* outer
                # transaction, silently breaking every subsequent statement in this session
                # (including the final commit below). The savepoint scopes the failure to just
                # this one edge so the rest of the course's data still saves correctly.
                try:
                    async with session.begin_nested():
                        await session.execute(
                            prereq_query,
                            {
                                "target_course_id": course.course_id,
                                "prereq_course_id": prereq_id,
                                "logic_type": group.logic_type,
                                "minimum_grade": group.minimum_grade
                            }
                        )
                except Exception as db_err:
                    print(f"⚠️ Skipping prerequisite edge {prereq_id} -> {course.course_id} (Parent course not yet ingested).")
                    
    # Commit the changes securely to the database
    await session.commit()
    print(f"💾 Permanently synced and embedded {course.course_id} into Postgres.")