from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://catalog.csueastbay.edu/content.php?catoid=44&navoid=42189', wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        
        print("Page title:", page.title())
        links = page.locator('a').all()
        course_links = 0
        for l in links:
            text = l.inner_text().strip()
            if text.startswith("CS ") or text.startswith("MATH "):
                print("Found course link:", text)
                course_links += 1
                if course_links > 5:
                    break
                    
        print(f"Total links: {len(links)}")
        browser.close()

if __name__ == "__main__":
    main()
