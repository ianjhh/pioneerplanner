import asyncio
import os
from sqlalchemy import text
from database import AsyncSessionLocal
from langchain_ollama import OllamaEmbeddings

OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

embeddings_engine = OllamaEmbeddings(
    model=OLLAMA_EMBED_MODEL,
    base_url=OLLAMA_BASE_URL,
)

async def main():
    async with AsyncSessionLocal() as session:
        # Fetch all courses missing embeddings
        res = await session.execute(text("SELECT course_id, title, description FROM courses WHERE embedding IS NULL"))
        rows = res.fetchall()
        
        if not rows:
            print("All courses have embeddings.")
            return

        print(f"Generating embeddings for {len(rows)} courses...")
        
        for i, row in enumerate(rows):
            course_id, title, description = row
            text_to_embed = f"{title}: {description}"
            
            try:
                # Generate embedding
                embedding_vector = await embeddings_engine.aembed_query(text_to_embed)
                
                # Update DB
                await session.execute(text("""
                    UPDATE courses
                    SET embedding = :embedding
                    WHERE course_id = :course_id
                """), {
                    "embedding": str(embedding_vector),
                    "course_id": course_id
                })
                
                if (i + 1) % 100 == 0:
                    await session.commit()
                    print(f"Processed {i + 1}/{len(rows)}...")
                    
            except Exception as e:
                print(f"Failed embedding {course_id}: {e}")
                
        await session.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
