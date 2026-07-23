import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text('SELECT COUNT(*) FROM courses;'))
        print('COURSES COUNT:', res.fetchone()[0])
        
asyncio.run(main())
