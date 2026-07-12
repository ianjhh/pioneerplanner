import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv() 

# Database connection URL (matches docker-compose.yml)
# asyncpg driver for asynchronous operations
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a session factory
AsyncSessionLocal = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def test_connection():
    """Test the database connection and verify the vector extension."""
    async with AsyncSessionLocal() as session:
        try:
            # Execute a simple test query
            result = await session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
            row = result.fetchone()
            if row:
                print("✅ Successfully connected to Postgres!")
                print("✅ pgvector extension is active!")
            else:
                print("❌ pgvector extension not found.")
        except Exception as e:
            print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_connection())

