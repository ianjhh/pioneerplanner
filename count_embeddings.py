import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text('SELECT COUNT(*) FROM courses WHERE embedding IS NULL;'))
        print('COURSES WITHOUT EMBEDDING:', res.fetchone()[0])
        
asyncio.run(main())
