import asyncio
import httpx
from bs4 import BeautifulSoup
import re

async def main():
    url = 'https://catalog.csueastbay.edu/preview_course_nopop.php?catoid=44&coid=186883'
    headers={'User-Agent':'Mozilla/5.0'}
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        print('Status:', res.status_code)
        
        soup = BeautifulSoup(res.text, 'html.parser')
        block = soup.select_one('td.block_content')
        if not block:
            print("Block not found!")
            return
            
        text_content = block.get_text(separator=' ', strip=True)
        print("Raw text:")
        print(text_content[:300])
        print("...")
        print(text_content[-300:])
        
        prereq_match = re.search(r"Prerequisite[^:]*:(.*?)(?:\.|$)", text_content, re.IGNORECASE)
        print("Prereq match:", prereq_match)
        if prereq_match:
            print("Extracted prereq:", prereq_match.group(1))
            
asyncio.run(main())
