import asyncio
import random
import csv
import os
import re
from playwright.async_api import async_playwright, TimeoutError
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from langdetect import detect, detect_langs
from collections import deque

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

FILE = "CNN"
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

# -------- extract related article links --------
async def extract_related_links(page):
    try:
        await page.wait_for_selector("div.container_list-headlines-with-read-times__cards-wrapper", timeout=8000)
        
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        links = []
        
        article_selectors = [
            "a.container__link--type-article"
        ]

        for selector in article_selectors:
            articles = soup.select(selector)
            print(f"  Found {len(articles)} related links")
            
            for article in articles:
                href = article.get("href")
                if href:
                    if href.startswith('/'):
                        href = "https://edition.cnn.com" + href
                    elif not href.startswith('http'):
                        continue
                    
                    if "/category/" not in href and "/author/" not in href:
                        links.append(href)

        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)

        print(f"  Extracted {len(unique_links)} unique related links")
        return unique_links
    
    except Exception as e:
        print(f"  Error extracting related links: {e}")
        return []

# -------- fetch content and related links --------
async def fetch_article_content_and_links(context, url, retries=3, delay=2):
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

            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_selector("main.article__main", timeout=8000)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Extract article content
            paragraphs = soup.select(".article__content-container div.article__content p") 
            content = " ".join(p.get_text(strip=True) for p in paragraphs)

            def get_meta_content(property_name):
                tag = soup.find("meta", property=property_name)
                return tag["content"].strip() if tag and tag.get("content") else None

            title = get_meta_content("og:title")
            if title:
                title = re.sub(r"\s*\|\s*CNN$", "", title)
            site_name = get_meta_content("og:site_name")
            image_url = get_meta_content("og:image")

            related_links = await extract_related_links(page)

            await page.close()

            return {
                "title": title,
                "site_name": site_name,
                "image_url": image_url,
                "content": content if content.strip() else None,
                "related_links": related_links
            }

        except TimeoutError:
            print(f"  [Attempt {attempt}] Timeout for article: {url}")
        except Exception as e:
            print(f"  [Attempt {attempt}] Error scraping {url}: {e}")
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

        await asyncio.sleep(delay)

    return None

# -------- main crawler --------
async def scrape():
    start_url = "https://edition.cnn.com/2025/10/01/politics/supreme-court-agrees-to-hear-arguments-in-case-on-federal-reserve-independence"
    batch_size = 10
    target_total = 500
    
    scraped_links = set()
    failed_links = set()
    
    # queue for crawling (BFS approach)
    to_visit = deque([start_url])

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

        await context.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,otf}", lambda route: route.abort())
        await context.route("**/analytics**", lambda route: route.abort())
        await context.route("**/gtag**", lambda route: route.abort())
        await context.route("**/facebook.com**", lambda route: route.abort())
        await context.route("**/google-analytics**", lambda route: route.abort())
        await context.route("**/googletag**", lambda route: route.abort())
        await context.route("**/advertisement**", lambda route: route.abort())

        count = already_scraped
        write_header = not os.path.exists(CSV_PATH)

        while to_visit and count < target_total:
            current_url = to_visit.popleft()
            
            if current_url in scraped_links or current_url in failed_links:
                continue
            
            print(f"\n[{count + 1}/{target_total}] Crawling: {current_url[:80]}...")
            
            article_data = await fetch_article_content_and_links(context, current_url)
            
            if not article_data or not article_data["content"]:
                print(f"  -> Failed to get content")
                failed_links.add(current_url)
                continue
            
            content = article_data["content"]
            if not is_mostly_english(content):
                print("  -> Skipped (not enough English content)")
                failed_links.add(current_url)
                continue
            
            data = {
                "title": article_data["title"],
                "meta_image": article_data["image_url"],
                "content": content,
                "url": current_url,
                "label": article_data["site_name"]
            }
            save_to_csv(data, write_header)
            write_header = False
            
            scraped_links.add(current_url)
            count += 1
            print(f"  -> Scraped successfully ({count} total)")
            
            if count % batch_size == 0:
                print(f"*** Milestone: {count} articles scraped ***")
            
            related_links = article_data.get("related_links", [])
            new_links_added = 0
            for link in related_links:
                if link not in scraped_links and link not in failed_links and link not in to_visit:
                    to_visit.append(link)
                    new_links_added += 1
            
            if new_links_added > 0:
                print(f"  -> Added {new_links_added} new links to queue (queue size: {len(to_visit)})")
            
            if count >= target_total:
                print(f"\nTarget of {target_total} articles reached!")
                break
            
            await asyncio.sleep(random.uniform(1, 2))

        await context.close()
        await browser.close()

    print(f"\n=== Crawling Complete ===")
    print(f"New articles scraped: {count - already_scraped}")
    print(f"Total articles in file: {count}")
    print(f"Failed URLs: {len(failed_links)}")
    print(f"Remaining queue size: {len(to_visit)}")

if __name__ == '__main__':
    asyncio.run(scrape())