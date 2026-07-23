import asyncio
import csv
import re
from playwright.async_api import async_playwright
from sqlalchemy import text
from database import AsyncSessionLocal

CSV_PATH = "csueb_all_courses_detailed.csv"
CONCURRENCY_LIMIT = 5

# Regex to find course codes like "CS 201" or "MATH 1000"
COURSE_REGEX = re.compile(r"([A-Z]{2,4}\s\d{3,4})")

async def fetch_and_parse(context, row, sem, all_prereqs):
    target_course_id = row['code'].strip()
    url = row['url'].strip()
    
    if not url or not target_course_id:
        return
        
    async with sem:
        try:
            page = await context.new_page()
            
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            
            try:
                await page.wait_for_selector('td.block_content', timeout=5000)
            except Exception as e:
                # If it still doesn't load after 5 seconds, just skip this course
                await page.close()
                return

            block = page.locator('td.block_content')
            if await block.count() > 0:
                text_content = await block.first.inner_text()
                # Replace newlines with spaces so the regex can match across lines easily
                text_content = text_content.replace('\n', ' ')
                
                # Find the Prerequisite string
                prereq_match = re.search(r"Prerequisite[^:]*:(.*?)(?:\.|Possible Instructional Methods|Grading|$)", text_content, re.IGNORECASE)
                
                if prereq_match:
                    prereq_text = prereq_match.group(1)
                    
                    # Extract course codes
                    prereq_courses = COURSE_REGEX.findall(prereq_text)
                    prereq_courses = list(set([c.strip() for c in prereq_courses]))
                    
                    # Try to extract grade
                    min_grade = "C"
                    grade_match = re.search(r"grade (?:of |or )?([A-D][+-]?)", prereq_text, re.IGNORECASE)
                    if grade_match:
                        min_grade = grade_match.group(1).upper()
                        
                    for pc in prereq_courses:
                        if pc.upper() != target_course_id.upper():
                            all_prereqs.append({
                                "target_course_id": target_course_id,
                                "prereq_course_id": pc,
                                "logic_type": "AND",
                                "minimum_grade": min_grade
                            })
                            print(f"[{target_course_id}] -> {pc} ({min_grade})")
                            
            await page.close()
        except Exception as e:
            print(f"Error fetching {target_course_id}: {e}")
            try:
                await page.close()
            except:
                pass

async def main():
    print("Reading CSV...")
    courses = []
    with open(CSV_PATH, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            courses.append(row)
            
    print(f"Found {len(courses)} courses in CSV.")
    
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    all_prereqs = []
    
    print("Scraping prerequisites with Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Process in smaller chunks to avoid overwhelming the loop
        chunk_size = 50
        for i in range(0, len(courses), chunk_size):
            chunk = courses[i:i+chunk_size]
            tasks = [fetch_and_parse(context, c, sem, all_prereqs) for c in chunk]
            await asyncio.gather(*tasks)
            print(f"Processed {min(i+chunk_size, len(courses))} / {len(courses)}")

        await browser.close()

    print(f"Scraped a total of {len(all_prereqs)} prerequisite edges.")
    
    print("Updating database...")
    async with AsyncSessionLocal() as session:
        check_sql = text("""
            SELECT 1 FROM prerequisites 
            WHERE target_course_id = :target_course_id 
              AND prereq_course_id = :prereq_course_id;
        """)
        insert_sql = text("""
            INSERT INTO prerequisites (target_course_id, prereq_course_id, logic_type, minimum_grade)
            VALUES (:target_course_id, :prereq_course_id, :logic_type, :minimum_grade);
        """)
        
        inserted_count = 0
        for p in all_prereqs:
            try:
                # Clean any non-breaking spaces from the prereq ID
                p["prereq_course_id"] = p["prereq_course_id"].replace('\xa0', ' ').strip()
                # Ensure exactly one space between department and number
                p["prereq_course_id"] = re.sub(r'\s+', ' ', p["prereq_course_id"])
                
                exists = await session.execute(check_sql, {"target_course_id": p["target_course_id"], "prereq_course_id": p["prereq_course_id"]})
                if not exists.scalar():
                    res = await session.execute(insert_sql, p)
                    inserted_count += res.rowcount
            except Exception as e:
                print(f"Skipping invalid prerequisite {p['prereq_course_id']} for {p['target_course_id']}: {e}")
                # Rollback just the failed insert by committing the valid ones and restarting transaction
                # Wait, better to just let postgres abort the transaction. Actually, if a transaction is aborted, we can't continue using it.
                # It's better to just use a subtransaction or just start a new session inside the loop if it fails?
                # Easiest way in AsyncSession without nested transactions is to commit after each insert, or rollback on error.
                await session.rollback()
                
            else:
                await session.commit()
        
    print(f"Successfully inserted {inserted_count} new prerequisite rules into the database.")

if __name__ == "__main__":
    asyncio.run(main())
