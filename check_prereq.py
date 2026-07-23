import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT * FROM prerequisites WHERE target_course_id = 'CS 301';"))
        print('DB PREREQS:', res.fetchall())
        
        res = await session.execute(text("SELECT title, description FROM courses WHERE course_id = 'CS 301';"))
        print('DB DESC:', res.fetchall())
        
asyncio.run(main())
