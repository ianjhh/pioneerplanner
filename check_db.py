import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT * FROM prerequisites WHERE target_course_id='CS 301'"))
        print(res.fetchall())

if __name__ == "__main__":
    asyncio.run(main())
