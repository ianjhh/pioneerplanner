from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://catalog.csueastbay.edu/preview_course_nopop.php?catoid=44&coid=186883', wait_until='domcontentloaded')
        
        # Wait a bit just in case
        page.wait_for_timeout(2000)
        
        block = page.locator('td.block_content')
        if block.count() > 0:
            print("Found block:")
            print(block.first.inner_text()[:300])
        else:
            print("Block not found!")
            print(page.content()[:300])
        browser.close()

if __name__ == "__main__":
    main()
