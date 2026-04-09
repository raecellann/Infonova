import asyncio
import csv
import os
import random
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup
from collections import defaultdict

# CSV_PATH = "data/GMA_datasets.csv"
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "GMA_datasets.csv")


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

CATEGORIES = [
    "https://www.gmanetwork.com/news/archives/sports/",
    "https://www.gmanetwork.com/news/archives/topstories/",
    "https://www.gmanetwork.com/news/archives/news/",
    "https://www.gmanetwork.com/news/archives/money/",
    "https://www.gmanetwork.com/news/archives/lifestyle/",
    "https://www.gmanetwork.com/news/archives/scitech/",
    "https://www.gmanetwork.com/news/archives/showbiz/",
]

ARTICLES_PER_CATEGORY = 286
MAX_CONCURRENT_ARTICLES = 10  
BATCH_SIZE = 30  

csv_lock = asyncio.Lock()


def get_category_from_url(url):
    """Extract category name from article URL"""
    for category in CATEGORIES:
        category_name = category.rstrip('/').split('/')[-1]
        if f"/{category_name}/" in url:
            return category
    return None


async def save_to_csv(data):
    """Thread-safe CSV saving"""
    async with csv_lock:
        file_exists = os.path.exists(CSV_PATH)
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["meta_image", "title", "content", "url", "label"])
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)


async def fetch_article_content(context, url, title):
    """Fetch article content with reduced timeouts"""
    page = None
    try:
        page = await context.new_page()
        await page.goto(url, timeout=8000, wait_until="domcontentloaded")
        
       
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract meta image
        meta_image = ""
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            meta_image = og_image.get("content")
        
        # Extract content - try multiple selectors
        paragraphs = soup.select(
            "div.story_main p, div.article-body p, div.ncaa_article_body p"
        )
        
        if not paragraphs:
            paragraphs = soup.select("article p, .content p, .article-content p")
        
        content = " ".join(p.get_text(strip=True) for p in paragraphs)

        if content.strip():
            return {
                "meta_image": meta_image,
                "title": title,
                "content": content,
                "url": url,
                "label": "GMA"
            }

    except Exception:
        pass  
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass

    return None


async def process_article_batch(context, articles, progress_counter, target):
    """Process multiple articles concurrently"""
    tasks = [fetch_article_content(context, url, title) for title, url in articles]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    saved = 0
    for result in results:
        if result and isinstance(result, dict) and result.get("content"):
            await save_to_csv(result)
            saved += 1
            progress_counter['count'] += 1
            print(f"  [{progress_counter['count']}/{target}] {result['title'][:55]}...")
    
    return saved


async def scrape_category(context, category_url, scraped_links, target_per_category, already_scraped_count):
    """Scrape articles from a specific category with concurrent processing"""
    needed = target_per_category - already_scraped_count
    
    if needed <= 0:
        print(f"\nCategory: {category_url}")
        print(f"  Already complete! ({already_scraped_count}/{target_per_category})")
        return 0
    
    category_name = category_url.split('/')[-2].upper()
    print(f"\nScraping category: {category_name}")
    print(f"Target: {target_per_category} | Have: {already_scraped_count} | Need: {needed}")
    
    archive_page = None
    try:
        archive_page = await context.new_page()
        print(f"  Loading category page...")
        await archive_page.goto(category_url, timeout=20000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"  ERROR: Failed to load category page: {e}")
        if archive_page:
            await archive_page.close()
        return 0
    
    progress = {'count': already_scraped_count}
    total_saved = 0
    consecutive_no_new = 0
    max_consecutive_no_new = 15
    
    pending_articles = []
    
    while total_saved < needed:
        # Scroll with reduced wait time
        await archive_page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await archive_page.wait_for_timeout(1500) 

        html = await archive_page.content()
        soup = BeautifulSoup(html, "html.parser")
        article_links = soup.find_all("a", class_="story_link story")

        new_found = False
        
        for a in article_links:
            title = a.get("title")
            link = a.get("href")

            if not link or link in scraped_links:
                continue

            new_found = True
            scraped_links.add(link)
            pending_articles.append((title, link))

            # Process in batches for better concurrency
            if len(pending_articles) >= BATCH_SIZE:
                saved = await process_article_batch(context, pending_articles, progress, target_per_category)
                total_saved += saved
                pending_articles = []
                
                if total_saved >= needed:
                    break

        if pending_articles and total_saved < needed:
            saved = await process_article_batch(context, pending_articles, progress, target_per_category)
            total_saved += saved
            pending_articles = []

        if not new_found:
            consecutive_no_new += 1
            current_total = already_scraped_count + total_saved
            print(f"  No new links ({consecutive_no_new}/{max_consecutive_no_new}). At {current_total}/{target_per_category}...")
            if consecutive_no_new >= max_consecutive_no_new:
                print(f"  Max scrolls reached. Stopping at {current_total} articles.")
                break
        else:
            consecutive_no_new = 0

        if total_saved >= needed:
            print(f"  Target reached!")
            break
    
    await archive_page.close()
    return total_saved


async def scrape():
    """Main scraping function"""
    target_total = ARTICLES_PER_CATEGORY * len(CATEGORIES)
    scraped_links = set()
    category_counts = defaultdict(int)

    already_scraped = 0
    if os.path.exists(CSV_PATH):
        print("Reading existing CSV file...")
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row["url"]
                scraped_links.add(url)
                
                category = get_category_from_url(url)
                if category:
                    category_counts[category] += 1
                
        already_scraped = len(scraped_links)
        print(f"Found {already_scraped} existing articles\n")
        print("Per-category breakdown:")
        for cat in CATEGORIES:
            count = category_counts[cat]
            status = "DONE" if count >= ARTICLES_PER_CATEGORY else f"{count}/{ARTICLES_PER_CATEGORY}"
            print(f"  {cat.split('/')[-2]:12} : {status}")

    print(f"\nTarget: {target_total} articles ({ARTICLES_PER_CATEGORY} per category x {len(CATEGORIES)} categories)")
    print(f"Still need: {target_total - already_scraped} more articles\n")
    print("="*70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        user_agent = random.choice(USER_AGENTS)
        context = await browser.new_context(
            user_agent=user_agent,
            bypass_csp=True,
            java_script_enabled=True
        )

        total_scraped = 0
        
        for i, category in enumerate(CATEGORIES):
            print(f"\n[Category {i+1}/{len(CATEGORIES)}]")
            
            already_in_category = category_counts[category]
            
            try:
                scraped = await scrape_category(
                    context, category, scraped_links, 
                    ARTICLES_PER_CATEGORY, already_in_category
                )
            except Exception as e:
                print(f"  ERROR during scraping: {e}")
                scraped = 0
            
            total_scraped += scraped
            
            current_total = already_scraped + total_scraped
            category_total = already_in_category + scraped
            print(f"\nCategory summary: +{scraped} new (Total: {category_total}/{ARTICLES_PER_CATEGORY})")
            print(f"Overall progress: {current_total}/{target_total} ({current_total/target_total*100:.1f}%)")
            print("="*70)
            
            await asyncio.sleep(1)  

        await context.close()
        await browser.close()

    final_total = already_scraped + total_scraped
    print(f"\nScraping complete!")
    print(f"New articles: {total_scraped}")
    print(f"Total in file: {final_total}")
    print(f"Target: {target_total}")
    
    if final_total >= target_total:
        print("SUCCESS! Target reached!")
    else:
        print(f"Scraped {final_total}/{target_total} ({final_total/target_total*100:.1f}%)")


if __name__ == "__main__":
    asyncio.run(scrape())