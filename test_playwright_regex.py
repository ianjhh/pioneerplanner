from playwright.sync_api import sync_playwright
import re

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://catalog.csueastbay.edu/preview_course_nopop.php?catoid=44&coid=186883', wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        
        block = page.locator('td.block_content')
        if block.count() > 0:
            text = block.first.inner_text()
            print("--- FULL TEXT ---")
            print(text)
            print("-----------------")
            
            prereq_match = re.search(r"Prerequisite[^:]*:(.*?)(?:\.|$)", text.replace('\n', ' '), re.IGNORECASE)
            print("REGEX MATCH:", prereq_match)
            if prereq_match:
                print("GROUP 1:", prereq_match.group(1))
        browser.close()

if __name__ == "__main__":
    main()
