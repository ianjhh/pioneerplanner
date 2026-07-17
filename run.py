import os
import asyncio
import csv
import re
import traceback
from dotenv import load_dotenv

# Swapped to Ollama's local embedding engine
from langchain_ollama import OllamaEmbeddings

from agent import compiled_agent
from database import AsyncSessionLocal
from database_ops import save_course_to_db

load_dotenv()

# nomic-embed-text is the standard, well-supported Ollama embedding model
# (768 dimensions). mxbai-embed-large is a stronger alternative (1024 dims)
# if you want higher retrieval quality and don't mind the extra VRAM.
#
# IMPORTANT: whichever model you pick, its output dimension MUST match the
# vector column in your pgvector schema. OpenAI's text-embedding-3-small is
# 1536-dim, so if your Postgres schema was created against that, you'll need
# to migrate the column (e.g. ALTER TABLE ... ALTER COLUMN embedding TYPE
# vector(768)) before this will insert cleanly — it will NOT silently work
# with mismatched dimensions.
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

embeddings_engine = OllamaEmbeddings(
    model=OLLAMA_EMBED_MODEL,
    base_url=OLLAMA_BASE_URL,
)

# Matches "Units: 3", "Unit: 4", "Units:1-4", "Units: 3.0", etc. inside the
# free-text details/description field.
UNITS_RE = re.compile(r'Units?\s*:\s*([\d.]+(?:\s*-\s*[\d.]+)?)', re.IGNORECASE)


def extract_units(row: dict) -> str:
    """
    Determine the unit count for a course row.

    Prefers an explicit units/unit column. That column is empty for ~94% of
    this catalog, so for those rows we recover the real value out of the
    details text (it's almost always present as "Units: N") instead of
    silently guessing. Only falls back to a hardcoded default if neither
    source has it — should be rare.
    """
    units_val = row.get('units') or row.get('unit')
    if units_val:
        return units_val

    match = UNITS_RE.search(row.get('details', '') or '')
    if match:
        return match.group(1)

    return '3'  # true last resort


async def process_single_course(course_text: str, session) -> bool:
    """
    Transforms raw course text into a structured DAG using LangGraph,
    generates an embedding, and imports it into the database.
    """
    initial_state = {
        "raw_text": course_text,
        "extracted_course": None,
        "error_message": None,
        "retry_count": 0
    }

    # 1. Structured JSON extraction via LangGraph (Powered by local Ollama model in agent.py)
    final_state = await compiled_agent.ainvoke(initial_state)
    course_data = final_state.get("extracted_course")
    error_message = final_state.get("error_message")

    # A course that exhausted its retries while still failing validation
    # (error_message still set) must NOT be saved, even if extracted_course
    # holds an object — it's the last bad attempt, not a validated result.
    if not course_data or error_message:
        print(f"❌ Agent failed to produce a valid course after retries ({error_message}). Skipping.")
        return False

    print(f"🤖 Agent Extracted: [{course_data.department}] {course_data.course_id} - {course_data.title}")

    # 2. Vector computation (Powered by local Ollama embedding model)
    text_to_embed = f"{course_data.title}: {course_data.description}"
    try:
        embedding_vector = await embeddings_engine.aembed_query(text_to_embed)
    except Exception as e:
        print(f"❌ Error generating embedding for {course_data.course_id}: {e}")
        return False

    # 3. Secure commit to the database tables
    await save_course_to_db(session, course_data, embedding_vector)
    return True


async def main():
    csv_filename = "csueb_all_courses_detailed.csv"
    print(f"📂 Loading course data from {csv_filename}...")

    try:
        with open(csv_filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            course_rows = list(reader)
    except FileNotFoundError:
        print(f"❌ Error: '{csv_filename}' not found. Please ensure the file is in the same directory.")
        return

    total_discovered = len(course_rows)
    if total_discovered == 0:
        print("⚠️ No courses found in the CSV file.")
        return

    # Local Ollama is running on your own hardware, not a rate-limited API, so
    # the bottleneck is now GPU/CPU throughput rather than requests-per-minute.
    # Ollama's default parallel request limit (OLLAMA_NUM_PARALLEL) is small
    # (commonly 4), and requests beyond that just queue rather than fail — but
    # a concurrency of 10 will mostly just pile up in that queue on a single
    # GPU. Dropping to 3-4 keeps a modest pipeline going without swamping one
    # model instance. Raise this if you've set OLLAMA_NUM_PARALLEL higher and
    # have the VRAM to back it.
    CONCURRENCY_LIMIT = int(os.getenv("CONCURRENCY_LIMIT", "4"))
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async def sem_process(idx, row):
        """Wrapper to safely execute LangGraph tasks concurrently with isolated DB sessions."""
        async with semaphore:
            # Safely extract units
            units_val = extract_units(row)

            # Format the CSV row
            raw_text = (
                f"Course Code: {row.get('code', 'Unknown')}\n"
                f"Title: {row.get('title', 'Unknown')}\n"
                f"Prerequisites: {row.get('prerequisites', 'None')}\n"
                f"Availability: {row.get('availability', 'Unknown')}\n"
                f"Details/Description: {row.get('details', '')}\n"
                f"URL: {row.get('url', '')}\n"
                f"Units: {units_val}"
            )

            # Sanitize curly braces to prevent LangChain prompt parsing bugs
            safe_course_text = raw_text.replace("{", "[").replace("}", "]")

            try:
                # Open a fresh database session purely for this one course
                async with AsyncSessionLocal() as session:
                    return await process_single_course(safe_course_text, session)
            except Exception as e:
                print(f"❌ Failed to process record [{idx + 1}]: {e}")
                traceback.print_exc()

    print(f"\n⚡ Initializing Concurrent Local Ollama Pipeline for {total_discovered} courses...")

    # Fire off all courses concurrently
    tasks = [sem_process(idx, row) for idx, row in enumerate(course_rows)]
    results = await asyncio.gather(*tasks)

    successful_extractions = sum(1 for r in results if r is True)

    print("\n================ INGESTION RUN COMPLETE ================")
    print(f"🏁 Comprehensive catalog parsing, DAG construction, and vector embedding finalized!")
    print(f"📊 Summary: Successfully processed and saved {successful_extractions} out of {total_discovered} courses into Postgres.")
    print("========================================================\n")


if __name__ == "__main__":
    asyncio.run(main())