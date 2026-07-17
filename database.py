import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
import os

load_dotenv()

# Database connection URL (matches docker-compose.yml)
# asyncpg driver for asynchronous operations
DATABASE_URL = os.getenv("DB_URL")

# pool_pre_ping: pings each connection before handing it to your code. If
# Docker's networking (vpnkit/WSL2) silently dropped a pooled connection —
# common under bursty concurrent load on Windows — SQLAlchemy transparently
# discards it and opens a fresh one instead of raising WinError 1225 up
# into your application code.
#
# pool_size / max_overflow: sized comfortably above CONCURRENCY_LIMIT so
# concurrent course-processing tasks each get their own connection without
# contention.
#
# connect_args timeout: gives Docker's port-forwarding layer a little more
# grace on a slow handshake before asyncpg gives up and raises.
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=5,
    connect_args={"timeout": 10},
)

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
    asyncio.run(test_connection())