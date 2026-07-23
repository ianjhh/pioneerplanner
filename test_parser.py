import asyncio
from query_parser import parse_natural_language_query

async def main():
    res = await parse_natural_language_query("what cs course does not require cs301 as prerequisite and is 3rd or 4th year")
    print(res.model_dump_json(indent=2))

asyncio.run(main())
