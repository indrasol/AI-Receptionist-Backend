from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime


class UrlScrapeRequest(BaseModel):
    """Request schema for URL scraping"""
    url: str
    max_depth: Optional[int] = 3  # Maximum depth for subdomain/sub-URL scraping
    include_subdomains: Optional[bool] = True
    include_subpages: Optional[bool] = True
    receptionist_id: Optional[str] = None  # UUID as string


class ScrapedContent(BaseModel):
    """Schema for individual scraped content"""
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    meta_description: Optional[str] = None
    headings: Optional[List[str]] = None
    links: Optional[List[str]] = None
    images: Optional[List[str]] = None
    scraped_at: datetime
    status_code: Optional[int] = None
    error: Optional[str] = None
    quality_analysis: Optional[Dict[str, Any]] = None


class UrlScrapeResponse(BaseModel):
    """Response schema for URL scraping"""
    message: str
    total_urls_scraped: int
    successful_scrapes: int
    failed_scrapes: int
    scraped_content: List[ScrapedContent]
    subdomains_found: Optional[List[str]] = None
    subpages_found: Optional[List[str]] = None
    processing_time_seconds: Optional[float] = None
