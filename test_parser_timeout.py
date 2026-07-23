import asyncio
from query_parser import parse_natural_language_query

async def main():
    try:
        print("Starting parse...")
        res = await asyncio.wait_for(parse_natural_language_query('what cs course is in spring'), timeout=10)
        print("Result:", res)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
