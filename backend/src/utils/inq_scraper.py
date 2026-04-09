import asyncio
import random
import csv
import os
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone17,1; CPU iPhone OS 18_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

# CSV_PATH = os.path.join("../data", "INQUIRER_datasets.csv")
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "INQUIRER_datasets.csv")
CSV_PATH = os.path.abspath(CSV_PATH)

os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

def save_to_csv(data, write_header=False):
    """Save article data to CSV file"""
    file_exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["meta_image", "title", "content", "url", "label"]
        )
        if write_header and not file_exists:
            writer.writeheader()
        writer.writerow(data)
    print(f"✓ Saved: {data['title'][:60]}...")

async def scrape_article_content(page, url, retries=3):
    """Scrape individual article content and meta image with retry logic"""
    for attempt in range(retries):
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)  # Reduced wait time

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract meta image (OpenGraph or Twitter card)
            meta_image = None
            
           
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                meta_image = og_image.get('content')
           
            if not meta_image:
                twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
                if twitter_image and twitter_image.get('content'):
                    meta_image = twitter_image.get('content')
            
            if not meta_image:
                featured_img = soup.select_one('.wp-post-image, .featured-image img, article img')
                if featured_img and featured_img.get('src'):
                    meta_image = featured_img.get('src')
            
            content_selectors = [
                "#article_content p",
                ".entry-content p", 
                ".post-content p",
                ".article-body p",
                "article .content p"
            ]
            
            content_paragraphs = []
            for selector in content_selectors:
                content_paragraphs = soup.select(selector)
                if content_paragraphs:
                    break
            
            content = " ".join([p.get_text(strip=True) for p in content_paragraphs if p.get_text(strip=True)])
            
            if len(content) > 100:
                return {
                    'content': content,
                    'meta_image': meta_image if meta_image else ''
                }
            else:
                return None
            
        except TimeoutError:
            if attempt < retries - 1:
                print(f"⚠️  Timeout on attempt {attempt + 1}, retrying...")
                await asyncio.sleep(2)
                continue
            else:
                print(f"❌ Failed after {retries} attempts: {url}")
                return None
        except Exception as e:
            if attempt < retries - 1:
                print(f"⚠️  Error on attempt {attempt + 1}: {e}, retrying...")
                await asyncio.sleep(2)
                continue
            else:
                print(f"❌ Error scraping article {url}: {e}")
                return None

async def extract_article_links(page):
    """Extract article links from current page"""
    try:
        await page.wait_for_load_state('networkidle', timeout=15000)
    except TimeoutError:
        print("⚠️  Page didn't reach networkidle, continuing anyway...")
    
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")
    
    articles = []
    
    #different article selectors for Inquirer.net
    selectors = [
        "article.post",
        ".post-item", 
        ".entry",
        ".story-item",
        "article"
    ]
    
    for selector in selectors:
        articles = soup.select(selector)
        if articles and len(articles) > 3:  
            print(f"Found {len(articles)} articles using selector: {selector}")
            break
    
    
    if not articles or len(articles) < 3:
        print("Using fallback method to find articles...")
        all_links = soup.find_all('a', href=True)
        
        potential_articles = []
        seen_urls = set()
        
        for link in all_links:
            href = link.get('href', '')
            title = link.get_text(strip=True)
            
            # Filter for article-like links
            if (href and title and 
                len(title) > 30 and  # Substantial title
                href not in seen_urls and
                ('newsinfo.inquirer.net' in href or href.startswith('/')) and
                not any(skip in href.lower() for skip in [
                    '#', 'javascript:', 'mailto:', 'category', 'tag', 'author', 
                    'search', 'page/', '.jpg', '.png', '.pdf', '/page/'
                ]) and
                not any(skip in title.lower() for skip in [
                    'read more', 'continue reading', 'home', 'about', 'contact', 
                    'menu', 'subscribe', 'sign up'
                ])):
                
                full_url = href if href.startswith('http') else f"https://newsinfo.inquirer.net{href}"
                seen_urls.add(href)
                
                potential_articles.append({
                    'title': title,
                    'link': full_url
                })
        
        return potential_articles[:25] 
    
    
    article_data = []
    seen_urls = set()
    
    for article in articles:
        # Look for title link within article
        title_link = (article.select_one('h2 a') or 
                     article.select_one('h3 a') or 
                     article.select_one('h1 a') or
                     article.select_one('.entry-title a') or
                     article.select_one('a'))
        
        if title_link:
            title = title_link.get_text(strip=True)
            href = title_link.get('href', '')
            
            if title and href and len(title) > 20 and href not in seen_urls:
                if href.startswith('/'):
                    href = f"https://newsinfo.inquirer.net{href}"
                
                seen_urls.add(href)
                article_data.append({
                    'title': title,
                    'link': href
                })
    
    return article_data

async def handle_verification(page):
    """Handle verification, CAPTCHA, or bot detection - SIMPLIFIED"""
    try:
        await page.wait_for_timeout(2000)
        
        content = await page.content()
        title = await page.title()
        
        verification_found = False
        verification_phrases = ['verify you are human', 'checking your browser', 
                              'security check', 'cloudflare', 'captcha', 'challenge']
        
        if any(phrase in content.lower() for phrase in verification_phrases):
            verification_found = True
        
        if any(word in title.lower() for word in ['verify', 'captcha', 'challenge', 'checking', 'security']):
            verification_found = True
        
        if verification_found:
            print("⚠️  Verification/CAPTCHA detected!")
            print("🚨 PLEASE SOLVE THE VERIFICATION IN THE BROWSER WINDOW NOW!")
            print("Waiting 45 seconds for you to complete it...")
            
            for i in range(9):  
                await page.wait_for_timeout(5000)
                current_title = await page.title()
                
                # Check if verification is cleared
                if not any(word in current_title.lower() for word in ['verify', 'captcha', 'challenge', 'checking']):
                    print("✅ Verification completed!")
                    await page.wait_for_timeout(3000)
                    return
                    
                if i % 2 == 0:
                    print(f"Still waiting... {45 - (i+1)*5} seconds remaining")
            
            print("⏰ Time's up, continuing anyway...")
            await page.wait_for_timeout(5000)
        else:
            print("✅ No verification detected")
            
    except Exception as e:
        print(f"⚠️  Error checking verification: {e}")

async def click_next_page(page):
    """Navigate to next page - IMPROVED"""
    print("🔍 Looking for Next button...")
    
    try:
        
        try:
            await page.wait_for_load_state('networkidle', timeout=10000)
        except TimeoutError:
            print("⚠️  Page didn't stabilize, continuing...")
        
        current_url = page.url
        print(f"Current URL: {current_url}")
        
        # Extract current page number
        import re
        page_match = re.search(r'/page/(\d+)', current_url)
        current_page = int(page_match.group(1)) if page_match else 1
        next_page_num = current_page + 1
        
        # Try to construct next page URL directly
        if '/page/' in current_url:
            next_url = re.sub(r'/page/\d+', f'/page/{next_page_num}', current_url)
        else:
            # Add /page/2 to the URL
            next_url = current_url.rstrip('/') + '/page/2'
        
        print(f"🔗 Trying direct navigation to: {next_url}")
        
        try:
            await page.goto(next_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            new_url = page.url
            if f'/page/{next_page_num}' in new_url or (next_page_num == 2 and '/page/2' in new_url):
                print(f"✅ Successfully navigated to page {next_page_num}")
                return True
            else:
                print("❌ Failed to navigate to next page")
                return False
                
        except Exception as e:
            print(f"⚠️  Direct navigation failed: {e}")
            
            # Fallback: try clicking next button
            next_selectors = [
                '.wp-pagenavi .nextpostslink',
                '.pagination .next',
                'a[rel="next"]',
                '.nav-links .next',
                '.page-numbers.next',
                'a.next'
            ]
            
            for selector in next_selectors:
                try:
                    next_btn = await page.query_selector(selector)
                    if next_btn:
                        is_visible = await next_btn.is_visible()
                        if is_visible:
                            print(f"Found next button: {selector}")
                            await next_btn.scroll_into_view_if_needed()
                            await page.wait_for_timeout(1000)
                            await next_btn.click()
                            await page.wait_for_load_state('domcontentloaded', timeout=15000)
                            await page.wait_for_timeout(2000)
                            return True
                except Exception:
                    continue
            
            print("❌ Could not find or click next button")
            return False
        
    except Exception as e:
        print(f"❌ Error in navigation: {e}")
        return False

async def scrape_inquirer_world():
    """Main scraping function"""
    TARGET_ARTICLES = 2020
    start_page = 235 
    start_url = f"https://newsinfo.inquirer.net/category/latest-stories/world-latest-stories/page/{start_page}"
    
    scraped_links = set()
    total_scraped = 0
    
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                link = row.get('url') or row.get('link', '')
                if link:
                    scraped_links.add(link)
        total_scraped = len(scraped_links)
        print(f"📚 Loaded {total_scraped} existing articles")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            })
        """)
        
        list_page = await context.new_page()
        content_page = await context.new_page()
        
        try:
            print(f"🚀 Starting scrape from: {start_url}")
            print(f"🎯 Target: {TARGET_ARTICLES} articles")
            print(f"📊 Already have: {total_scraped} articles")
            print(f"📈 Need: {TARGET_ARTICLES - total_scraped} more articles\n")
            
            await list_page.goto(start_url, timeout=60000)
            await handle_verification(list_page)
            
            try:
                await list_page.wait_for_load_state('networkidle', timeout=20000)
            except TimeoutError:
                print("⚠️  Initial page didn't load fully, continuing...")
            
            page_num = start_page
            write_header = not os.path.exists(CSV_PATH)
            consecutive_failures = 0
            max_consecutive_failures = 3
            
            while page_num <= 300 and total_scraped < TARGET_ARTICLES:
                print(f"\n{'='*60}")
                print(f"📄 PAGE {page_num}")
                print(f"📈 Progress: {total_scraped}/{TARGET_ARTICLES} articles ({(total_scraped/TARGET_ARTICLES)*100:.1f}%)")
                print(f"{'='*60}")
                
                articles = await extract_article_links(list_page)
                print(f"🔍 Found {len(articles)} articles on page {page_num}")
                
                if len(articles) == 0:
                    consecutive_failures += 1
                    print(f"⚠️  No articles found! Failure {consecutive_failures}/{max_consecutive_failures}")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        print("❌ Too many consecutive failures. Stopping.")
                        break
                    
                    if not await click_next_page(list_page):
                        break
                    page_num += 1
                    await asyncio.sleep(2)
                    continue
                
                consecutive_failures = 0 
                new_articles_this_page = 0
                
                for idx, article in enumerate(articles, 1):
                    if total_scraped >= TARGET_ARTICLES:
                        print(f"\n🎯 Target of {TARGET_ARTICLES} articles reached!")
                        break
                    
                    title = article['title']
                    link = article['link']
                    
                    if link in scraped_links:
                        print(f"[{idx}/{len(articles)}] ⏭️  Skip (exists): {title[:50]}...")
                        continue
                    
                    print(f"[{idx}/{len(articles)}] 📰 Scraping: {title[:50]}...")
                    result = await scrape_article_content(content_page, link)
                    
                    if result:
                        article_data = {
                            'meta_image': result['meta_image'],
                            'title': title,
                            'content': result['content'],
                            'url': link,
                            'label': 'Inquirer'
                        }
                        
                        save_to_csv(article_data, write_header)
                        write_header = False
                        
                        scraped_links.add(link)
                        new_articles_this_page += 1
                        total_scraped += 1
                    
                        await asyncio.sleep(0.5)  
                    else:
                        print(f"[{idx}/{len(articles)}] ❌ Failed: {title[:40]}")
                
                print(f"\n✅ Page {page_num} complete: +{new_articles_this_page} new articles")
                print(f"📊 Total: {total_scraped}/{TARGET_ARTICLES}")
                
                if total_scraped >= TARGET_ARTICLES:
                    print(f"\n🎉 TARGET REACHED!")
                    break
                
                if not await click_next_page(list_page):
                    print("⚠️  Cannot navigate to next page. Stopping.")
                    break
                
                page_num += 1
                await asyncio.sleep(1.5) 
        except KeyboardInterrupt:
            print("\n\n⚠️  Scraping interrupted by user (Ctrl+C)")
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n🔒 Closing browser...")
            await browser.close()
    
    print(f"\n{'='*60}")
    print(f"🎉 SCRAPING SESSION COMPLETE!")
    print(f"{'='*60}")
    print(f"📊 Total articles in database: {total_scraped}")
    print(f"🎯 Target: {TARGET_ARTICLES}")
    print(f"📈 Progress: {(total_scraped/TARGET_ARTICLES)*100:.1f}%")
    print(f"📁 Data saved to: {CSV_PATH}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(scrape_inquirer_world())