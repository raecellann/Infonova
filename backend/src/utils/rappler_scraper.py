import asyncio
import random
import csv
import os
from playwright.async_api import async_playwright, TimeoutError
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from langdetect import detect, detect_langs

# user agents
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone17,1; CPU iPhone OS 18_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

# extra headers
HEADERS = {
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

FILE = "RAPPLER"
CSV_PATH = f"../data/{FILE}_datasets.csv"

# -------- save data to CSV --------
os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
def save_to_csv(data, write_header=False):
    file_exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["meta_image", "title", "content", "url", "label"]
        )
        if write_header and not file_exists:
            writer.writeheader()
        writer.writerow(data)

def is_mostly_english(text, threshold=0.9):
    try:
        langs = detect_langs(text)
        for lang in langs:
            if lang.lang == 'en' and lang.prob >= threshold:
                return True
        return False
    except Exception:
        return False

# -------- fetch content and source --------
async def fetch_article_content(context, url, retries=3, delay=2):
    for attempt in range(1, retries + 1):
        page = None
        try:
            page = await context.new_page()
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
                delete navigator.__proto__.webdriver;
            """)
            # await handle_verification(page)

            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_selector("div.article-main-section, div.post-single__content.entry-content, div.post-single__summary", timeout=8000)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            selectors = [
                "div.article-main-section, div.post-single__content.entry-content, div.post-single__summary",
            ]
            for selector in selectors:
                paragraphs = soup.select(selector) 
                content = " ".join(p.get_text(strip=True) for p in paragraphs)

            def get_meta_content(property_name):
                tag = soup.find("meta", property=property_name)
                return tag["content"].strip() if tag and tag.get("content") else None

            title = get_meta_content("og:title")
            site_name = get_meta_content("og:site_name")
            image_url = get_meta_content("og:image")

            return {
                "title": title,
                "site_name": site_name,
                "image_url": image_url,
                "content": content if content.strip() else None
            }

        except TimeoutError:
            print(f"[Attempt {attempt}] Timeout for article: {url}")
        except Exception as e:
            print(f"[Attempt {attempt}] Error scraping {url}: {e}")
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

        await asyncio.sleep(delay)

    return None

# -------- older posts  --------
async def click_older_posts_button(page, max_retries=3):
    selectors = ['a.pagination__link.pagination__load-more.button.button__bg-secondary']

    for attempt in range(max_retries):
        try:
            await page.wait_for_timeout(2000)

            for selector in selectors:
                try:
                    # print(f"Trying selector: {selector}")

                    element = await page.wait_for_selector(selector, timeout=5000)

                    if element:
                        is_visible = await element.is_visible()
                        is_enabled = await element.is_enabled()

                        if is_visible and is_enabled:
                            print(f"Found button: {selector}")
                            await element.scroll_into_view_if_needed()
                            await page.wait_for_timeout(1000)
                            await element.click()
                            await page.wait_for_timeout(4000)
                            return True
                        else:
                            print(f"Button found but not visible/enabled: visible={is_visible}, enabled={is_enabled}")

                except Exception as e:
                    print(f"Selector {selector} failed: {e}")
                    continue
            print("No older posts button found - might have reached end of articles")
            return False

        except Exception as e:
            print(f"Attempt {attempt + 1} failed to click older posts: {e}")
            await page.wait_for_timeout(2000)

    return False

# -------- extract links --------
async def extract_article_links(page):
    await page.wait_for_selector("div.archive-article__content a.archive-article__eyebrow", timeout=8000)
    
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")
    links = []

    articles = soup.find_all("article", id=lambda x: x and x.startswith("post-"))

    for article in articles:
        title_element = article.select_one("h2 > a")
        print(f"Found {len(articles)} potential articles")
        
        if title_element:
            href = title_element.get("href")
            if href:
                if href.startswith('/'):
                    href = "https://www.rappler.com" + href
                elif not href.startswith('http'):
                    continue
                
                if "/category/" not in href and "/author/" not in href:
                    links.append({"url": href})

    seen = set()
    unique_links = []
    for item in links:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique_links.append(item)

    print(f"Extracted {len(unique_links)} unique article links")
    return unique_links

# -------- main scraper --------
async def scrape():
    start_url = "https://www.rappler.com/latest/"
    batch_size = 10
    target_total = 2000
    scraped_links = set()
    failed_links = set()

    # resume
    already_scraped = 0
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scraped_links.add(row["url"])
        already_scraped = len(scraped_links)
        print(f"Resuming... {already_scraped} already scraped.")

    if already_scraped >= target_total:
        print(f"Already have {already_scraped} articles (>= {target_total}). Nothing to do.")
        return

    to_scrape = target_total - already_scraped
    print(f"Will scrape {to_scrape} new articles (target total = {target_total})")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-extensions',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-automation',
                '--disable-infobars',
                '--window-size=1920,1080'
            ]
        )

        user_agent = random.choice(USER_AGENTS)
        context = await browser.new_context(
            user_agent=user_agent, 
            extra_http_headers=HEADERS, 
            accept_downloads=False, 
            ignore_https_errors=True,
            color_scheme='dark'
        )

        stealth = Stealth()
        await stealth.apply_stealth_async(context)

        # block unnecessary resources
        await context.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,otf}", lambda route: route.abort())
        await context.route("**/analytics**", lambda route: route.abort())
        await context.route("**/gtag**", lambda route: route.abort())
        await context.route("**/facebook.com**", lambda route: route.abort())
        await context.route("**/google-analytics**", lambda route: route.abort())
        await context.route("**/googletag**", lambda route: route.abort())
        await context.route("**/advertisement**", lambda route: route.abort())

        main_page = await context.new_page()

        try:
            print("Loading main page...")
            await main_page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """)
            await main_page.goto(start_url, timeout=20000, wait_until='domcontentloaded')
            await main_page.wait_for_timeout(8000)
            content_loaded = False
            selectors = [
                "main.site-main.container"
            ]
            for selector in selectors:
                try:
                    await main_page.wait_for_selector(selector, timeout=5000)
                    print(f"Content loaded - found selector: {selector}")
                    content_loaded = True
                    break
                except:
                    continue
            
            if not content_loaded:
                print("Warning: Could not confirm content loaded, but continuing...")
            
            await main_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await main_page.wait_for_timeout(3000)
            await main_page.evaluate("window.scrollTo(0, 0)")
            await main_page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Failed to load main page: {e}")
            return

        count = already_scraped
        write_header = not os.path.exists(CSV_PATH)
        pages_without_new_articles = 0
        max_pages_without_new = float('inf')

        while count < target_total:
            print(f"\n--- Processing page (articles so far: {count}) ---")

            article_links = await extract_article_links(main_page)
            print(f"Found {len(article_links)} potential articles on this page")

            new_articles_this_page = 0

            for article_link in article_links:
                link = article_link["url"]

                if link in scraped_links or link in failed_links:
                    continue 

                print(f"Scraping: {link[:50]}...")
                article_data = await fetch_article_content(context, link)

                if not article_data:
                    print(f"  -> Failed to get content")
                    failed_links.add(link)
                    continue

                content = article_data["content"]
                if not is_mostly_english(content):
                    print("  -> Skipped (not enough English content)")
                    continue

                data = {
                    "meta_image": article_data["image_url"],
                    "title": article_data["title"],
                    "content": content,
                    "url": link,
                    "label": article_data["site_name"]
                }
                save_to_csv(data, write_header=write_header)
                write_header = False

                scraped_links.add(link)
                count += 1
                new_articles_this_page += 1
                print(f"  -> Scraped successfully ({count} total)")

                if count % batch_size == 0:
                    print(f"*** Milestone: {count} articles scraped ***")

                if count >= target_total:
                    break

            if new_articles_this_page == 0:
                pages_without_new_articles += 1
                print(f"No new articles on this page ({pages_without_new_articles}/{max_pages_without_new})")

                if pages_without_new_articles >= max_pages_without_new:
                    print("Too many pages without new articles. Stopping.")
                    break
            else:
                pages_without_new_articles = 0
                print(f"Got {new_articles_this_page} new articles from this page")

            if count >= target_total:
                break

            print("Attempting to load older posts...")
            success = await click_older_posts_button(main_page)
            if not success:
                print("Could not load older posts. Stopping.")
                break

            print("Loaded older posts, continuing...")

        await context.close()
        await browser.close()

    print(f"New articles scraped: {count - already_scraped}")
    print(f"Total articles in file: {count}")

if __name__ == '__main__':
    asyncio.run(scrape())
