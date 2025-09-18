"""
Web Scraping Service
Handles URL content scraping and subdomain/subpage discovery
"""

import asyncio
import logging
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Set, Optional
from datetime import datetime
import re
from app.schemas.scraper import ScrapedContent

logger = logging.getLogger(__name__)


class WebScraperService:
    """Service for web scraping and content extraction"""
    
    def __init__(self, use_selenium: bool = True):
        self.scraped_urls = set()
        self.max_depth = 3
        self.include_subdomains = True
        self.include_subpages = True
        self.selenium_driver = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Use webdriver-manager to automatically handle ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.selenium_driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Selenium driver initialized with webdriver-manager")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {str(e)}")
            raise e
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.selenium_driver:
            self.selenium_driver.quit()
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception as e:
            logger.error(f"Error extracting domain from {url}: {str(e)}")
            return ""
    
    def is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs belong to the same domain"""
        domain1 = self.extract_domain(url1)
        domain2 = self.extract_domain(url2)
        return domain1 == domain2
    
    def is_subdomain(self, url: str, base_domain: str) -> bool:
        """Check if URL is a subdomain of base domain"""
        try:
            url_domain = self.extract_domain(url)
            return url_domain.endswith(f".{base_domain}") or url_domain == base_domain
        except Exception:
            return False
    
    def normalize_url(self, url: str, base_url: str) -> str:
        """Normalize URL by resolving relative paths"""
        try:
            return urljoin(base_url, url)
        except Exception:
            return url
    

    def detect_content_quality(self, content: str, title: str, headings: List[str], links: List[str]) -> Dict[str, Any]:
        """Detect if we got enough meaningful content from the URL"""
        quality_score = 0
        issues = []
        recommendations = []
        
        # Check content length
        if not content or len(content.strip()) < 50:
            issues.append("Very short or empty content")
            quality_score -= 30
        elif len(content.strip()) < 200:
            issues.append("Short content (might be loading page)")
            quality_score -= 15
        else:
            quality_score += 20
        
        
        # Check title quality
        if not title or len(title.strip()) < 5:
            issues.append("Missing or very short title")
            quality_score -= 15
        elif title.lower() in ['loading', 'please wait', 'fetching']:
            issues.append("Title indicates loading state")
            quality_score -= 20
        else:
            quality_score += 10
        
        # Check headings
        if not headings or len(headings) == 0:
            issues.append("No headings found")
            quality_score -= 10
        elif len(headings) < 2:
            issues.append("Very few headings")
            quality_score -= 5
        else:
            quality_score += 10
        
        # Check for meaningful links
        if not links or len(links) < 3:
            issues.append("Very few links found")
            quality_score -= 10
        else:
            quality_score += 5
        
        
        # Determine overall quality
        if quality_score >= 20:
            quality_status = "excellent"
        elif quality_score >= 0:
            quality_status = "good"
        elif quality_score >= -20:
            quality_status = "fair"
        else:
            quality_status = "poor"
        
        return {
            "quality_score": quality_score,
            "quality_status": quality_status,
            "issues": issues,
            "recommendations": recommendations,
            "content_length": len(content.strip()) if content else 0,
            "has_title": bool(title and len(title.strip()) > 5),
            "has_headings": bool(headings and len(headings) > 0),
            "has_links": bool(links and len(links) > 0)
        }

    async def scrape_with_selenium(self, url: str, scraped_at: datetime) -> ScrapedContent:
        """Scrape using Selenium for JavaScript-heavy sites"""
        try:
            logger.info(f"Using Selenium to scrape {url}")
            self.selenium_driver.get(url)
            
            # Wait for content to load (adjust selectors based on common patterns)
            wait_selectors = [
                '.content', '.main-content', '.products', '.articles',
                '.feed', '.list', '.grid', '[data-testid]', '#app', '#root'
            ]
            
            for selector in wait_selectors:
                try:
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    from selenium.webdriver.common.by import By
                    
                    WebDriverWait(self.selenium_driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except Exception:
                    continue
            
            # Parse content directly from the driver
            return self.parse_html_content(self.selenium_driver, url, scraped_at, 200, method="selenium")
            
        except Exception as e:
            logger.error(f"Selenium scraping failed for {url}: {str(e)}")
            return ScrapedContent(
                url=url,
                scraped_at=scraped_at,
                error=f"Selenium error: {str(e)}"
            )

    def parse_html_content(self, driver, url: str, scraped_at: datetime, status_code: int, method: str = "selenium") -> ScrapedContent:
        """Parse HTML content using Selenium and extract data"""
        try:
            # Extract title
            title = driver.title.strip() if driver.title else ""
            
            # Extract meta description
            meta_description = ""
            try:
                meta_desc = driver.find_element("css selector", "meta[name='description']")
                meta_description = meta_desc.get_attribute("content").strip() if meta_desc else ""
            except:
                pass
            
            # Extract headings
            headings = []
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                try:
                    heading_elements = driver.find_elements("css selector", tag)
                    for heading in heading_elements:
                        text = heading.text.strip()
                        if text:
                            headings.append(text)
                except:
                    continue
            
            # Extract main content
            content = ""
            
            # Try to find main content areas
            main_content_selectors = [
                'main', 'article', '.content', '#content', '.main-content',
                '#main-content', '.post-content', '.entry-content', '.page-content'
            ]
            
            for selector in main_content_selectors:
                try:
                    content_elem = driver.find_element("css selector", selector)
                    if content_elem:
                        content = content_elem.text.strip()
                        break
                except:
                    continue
            
            # If no main content found, get body text
            if not content:
                try:
                    body = driver.find_element("css selector", "body")
                    content = body.text.strip()
                except:
                    pass
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content)
            
            # Extract links
            links = []
            try:
                link_elements = driver.find_elements("css selector", "a[href]")[:200]
                for link in link_elements:
                    href = link.get_attribute("href")
                    if href and href not in links:
                        # Filter out common non-content links
                        if not any(skip in href.lower() for skip in [
                            'mailto:', 'tel:', 'javascript:', '#', '?utm_', 'facebook.com', 
                            'twitter.com', 'linkedin.com', 'instagram.com', 'youtube.com'
                        ]):
                            links.append(href)
            except:
                pass
            
            # Extract images
            images = []
            try:
                img_elements = driver.find_elements("css selector", "img[src]")
                for img in img_elements:
                    src = img.get_attribute("src")
                    if src:
                        images.append(src)
            except:
                pass
            
            # Analyze content quality
            quality_analysis = self.detect_content_quality(content, title, headings, links)
            quality_analysis["scraping_method"] = method
            
            logger.info(f"Extracted {len(links)} links from {url}")
            
            return ScrapedContent(
                url=url,
                title=title,
                content=content[:5000] if content else None,
                meta_description=meta_description,
                headings=headings[:20] if headings else None,
                links=links[:200] if links else None,
                images=images[:20] if images else None,
                scraped_at=scraped_at,
                status_code=status_code,
                quality_analysis=quality_analysis
            )
            
        except Exception as e:
            logger.error(f"Error parsing HTML for {url}: {str(e)}")
            return ScrapedContent(
                url=url,
                scraped_at=scraped_at,
                status_code=status_code,
                error=f"Parsing error: {str(e)}"
            )

    async def scrape_url(self, url: str) -> ScrapedContent:
        """Scrape using Selenium for all websites"""
        scraped_at = datetime.now()
        
        try:
            logger.info(f"Scraping {url} with Selenium")
            
            if not self.selenium_driver:
                logger.error(f"Selenium driver not available for {url}")
                return ScrapedContent(
                    url=url,
                    scraped_at=scraped_at,
                    error="Selenium driver not available"
                )
            
            return await self.scrape_with_selenium(url, scraped_at)
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return ScrapedContent(
                url=url,
                scraped_at=scraped_at,
                error=str(e)
            )
    
    def discover_urls(self, base_url: str, scraped_content: ScrapedContent) -> List[str]:
        """Discover subdomains and subpages from scraped content"""
        discovered_urls = []
        base_domain = self.extract_domain(base_url)
        
        if not scraped_content.links:
            logger.warning(f"No links found in {scraped_content.url}")
            return discovered_urls
        
        logger.info(f"Found {len(scraped_content.links)} links in {scraped_content.url}")
        
        for link in scraped_content.links:
            if link in self.scraped_urls:
                continue
                
            link_domain = self.extract_domain(link)
            
            # Check if it's a subdomain
            if self.include_subdomains and self.is_subdomain(link, base_domain):
                discovered_urls.append(link)
                logger.info(f"Found subdomain: {link}")
            
            # Check if it's a subpage of the same domain (use if, not elif)
            if self.include_subpages and link_domain == base_domain and link != base_url:
                discovered_urls.append(link)
                logger.info(f"Found subpage: {link}")
        
        logger.info(f"Discovered {len(discovered_urls)} new URLs from {scraped_content.url}")
        return discovered_urls
    
    async def scrape_url_recursive(self, url: str, max_depth: int = 3, 
                                 include_subdomains: bool = True, 
                                 include_subpages: bool = True) -> List[ScrapedContent]:
        """Recursively scrape URL and its discovered subdomains/subpages"""
        self.max_depth = max_depth
        self.include_subdomains = include_subdomains
        self.include_subpages = include_subpages
        
        all_scraped_content = []
        urls_to_scrape = [(url, 0)]  # (url, depth)
        
        while urls_to_scrape:
            current_url, depth = urls_to_scrape.pop(0)
            
            if current_url in self.scraped_urls or depth > max_depth:
                continue
            
            self.scraped_urls.add(current_url)
            logger.info(f"Scraping {current_url} (depth: {depth})")
            
            # Scrape the current URL
            scraped_content = await self.scrape_url(current_url)
            all_scraped_content.append(scraped_content)
            
            # If scraping was successful, discover more URLs
            if scraped_content.status_code == 200 and depth < max_depth:
                discovered_urls = self.discover_urls(current_url, scraped_content)
                
                # Add discovered URLs to the queue
                for discovered_url in discovered_urls:
                    if discovered_url not in self.scraped_urls:
                        urls_to_scrape.append((discovered_url, depth + 1))
            
            # Add a small delay to be respectful to the server
            await asyncio.sleep(0.5)
        
        return all_scraped_content
