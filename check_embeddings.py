import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT COUNT(course_id) FROM courses WHERE embedding IS NOT NULL"))
        count = res.scalar()
        print(f"Courses with embeddings: {count}")

        res2 = await session.execute(text("SELECT COUNT(course_id) FROM courses"))
        count2 = res2.scalar()
        print(f"Total courses: {count2}")

if __name__ == "__main__":
    asyncio.run(main())
