import csv
import asyncio
import re
from sqlalchemy import text
from database import AsyncSessionLocal

def clean_title(title_raw: str) -> str:
    return re.sub(r'\(opens in a new tab\)', '', title_raw).strip()

def parse_units(units_raw: str, details_raw: str) -> int:
    if units_raw and units_raw.isdigit():
        return int(units_raw)
    match = re.search(r'Units?\s*:\s*(\d+)', details_raw or '', re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 3

async def seed():
    print("[SEED] Seeding Postgres database from csueb_all_courses_detailed.csv...")
    async with AsyncSessionLocal() as session:
        with open("csueb_all_courses_detailed.csv", mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                course_id = row['code'].strip()
                if not course_id:
                    continue
                
                title = clean_title(row.get('title', ''))
                department = course_id.split()[0] if ' ' in course_id else 'GENERAL'
                units = parse_units(row.get('units', ''), row.get('details', ''))
                description = row.get('details', '') or row.get('prerequisites', '') or 'No description available.'
                availability = ['Fall', 'Spring'] if 'Fall & Spring' in (row.get('availability') or '') else ['Fall']

                # Insert course
                query = text("""
                    INSERT INTO courses (course_id, title, department, units, description, availability)
                    VALUES (:course_id, :title, :department, :units, :description, :availability)
                    ON CONFLICT (course_id) DO UPDATE 
                    SET title = EXCLUDED.title,
                        department = EXCLUDED.department,
                        units = EXCLUDED.units,
                        description = EXCLUDED.description,
                        availability = EXCLUDED.availability;
                """)
                await session.execute(query, {
                    "course_id": course_id,
                    "title": title,
                    "department": department,
                    "units": units,
                    "description": description[:1000],
                    "availability": availability
                })
                count += 1
                
                # Parse basic prereqs if present (e.g. ACCT 210)
                prereq_raw = row.get('prerequisites', '')
                if prereq_raw:
                    found_prereqs = re.findall(r'\b([A-Z]{2,4}\s+\d{3}[A-Z]?)\b', prereq_raw)
                    for prereq_id in found_prereqs:
                        if prereq_id != course_id:
                            # Insert dummy parent course if it doesn't exist yet to satisfy FK
                            await session.execute(text("""
                                INSERT INTO courses (course_id, title, department, units, description, availability)
                                VALUES (:course_id, :title, :department, 3, 'Course catalog entry', ARRAY['Fall','Spring'])
                                ON CONFLICT (course_id) DO NOTHING;
                            """), {
                                "course_id": prereq_id,
                                "title": f"{prereq_id} Prerequisite",
                                "department": prereq_id.split()[0]
                            })

                            # Insert edge
                            await session.execute(text("""
                                INSERT INTO prerequisites (target_course_id, prereq_course_id, logic_type, minimum_grade)
                                VALUES (:target, :prereq, 'AND', 'C')
                                ON CONFLICT (target_course_id, prereq_course_id, logic_type) DO NOTHING;
                            """), {
                                "target": course_id,
                                "prereq": prereq_id
                            })

        await session.commit()
        print(f"[SUCCESS] Successfully seeded {count} courses into Postgres database!")

if __name__ == "__main__":
    asyncio.run(seed())
