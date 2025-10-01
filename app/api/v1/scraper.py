"""
URL Scraping API Endpoints
Handles web scraping requests and content extraction
"""

from fastapi import APIRouter, HTTPException, Depends
from app.schemas.scraper import UrlScrapeRequest, UrlScrapeResponse, ScrapedContent
from app.services.scraper_service import WebScraperService
from app.services.openai_service import OpenAIService
from app.utils.auth import get_current_user
from app.database_operations import get_supabase_client
import logging
import time
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Web Scraping"])


@router.post("/scrape-url")
async def scrape_url(
    request: UrlScrapeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Scrape URL and automatically generate chunks using OpenAI
    
    This endpoint combines web scraping with AI-powered chunk generation.
    It scrapes the website content and then uses OpenAI to create structured
    chunks suitable for AI assistant training.
    
    - **url**: The URL to scrape (e.g., "https://example.com")
    - **max_depth**: Maximum depth for recursive scraping (default: 3)
    - **include_subdomains**: Whether to include subdomains (default: true)
    - **include_subpages**: Whether to include subpages (default: true)
    
    Returns both the scraped content and the generated chunks.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting scrape-and-chunk for {request.url}")
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Step 1: Scrape the website
        async with WebScraperService(use_selenium=True) as scraper:
            scraped_content = await scraper.scrape_url_recursive(
                url=request.url,
                max_depth=request.max_depth or 3,
                include_subdomains=request.include_subdomains if request.include_subdomains is not None else True,
                include_subpages=request.include_subpages if request.include_subpages is not None else True
            )
        
        # Step 2: Generate chunks using OpenAI
        openai_service = OpenAIService()
        chunks = await openai_service.generate_chunks_from_scraped_data(
            scraped_data={
                "scraped_content": [content.model_dump() for content in scraped_content]
            },
            organization_id=str(organization_id)
        )
        
        # Step 3: Save chunks to database
        supabase = get_supabase_client()
        saved_chunks = []
        
        if chunks:
            # Add user info to chunks
            # Skip user tracking for now due to foreign key constraint
            for chunk in chunks:
                chunk["created_by_user_id"] = None
                chunk["receptionist_id"] = request.receptionist_id
            
            # Insert chunks into database
            result = supabase.table("chunks").insert(chunks).execute()
            saved_chunks = result.data if result.data else []

        # Step 4: Upload chunks to VAPI as files and update vapi_file_id
        from app.services.vapi_assistant import upload_chunk_to_vapi, sync_assistant_prompt
        for saved_chunk in saved_chunks:
            try:
                chunk_id = saved_chunk.get('id')
                chunk_name = saved_chunk.get('name', 'Unnamed Chunk')
                chunk_content = saved_chunk.get('content', '')
                bullets = saved_chunk.get('bullets', [])
                sample_questions = saved_chunk.get('sample_questions', [])
                
                # Upload to VAPI with complete information
                vapi_file_id = await upload_chunk_to_vapi(
                    chunk_id, 
                    chunk_name, 
                    chunk_content,
                    bullets=bullets,
                    sample_questions=sample_questions
                )
                
                # Update chunk with vapi_file_id
                if vapi_file_id:
                    supabase.table("chunks").update({"vapi_file_id": vapi_file_id}).eq("id", chunk_id).execute()
                    logger.info(f"Updated chunk {chunk_id} with VAPI file ID: {vapi_file_id}")
            except Exception as upload_error:
                logger.warning(f"Failed to upload chunk {chunk_id} to VAPI: {str(upload_error)}")
                # Continue with other chunks

        # Step 5: Sync assistant with updated knowledge base file IDs
        if request.receptionist_id:
            try:
                rec_row = supabase.table("receptionists").select("assistant_id").eq("id", request.receptionist_id).single().execute()
                assistant_id = rec_row.data.get("assistant_id") if rec_row.data else None
                if assistant_id:
                    await sync_assistant_prompt(assistant_id, request.receptionist_id)
                    logger.info(f"Successfully synced VAPI assistant {assistant_id} with scraped URL knowledge")
            except Exception as sync_error:
                logger.warning(f"Failed to sync VAPI assistant: {str(sync_error)}")
        
        processing_time = time.time() - start_time
        
        # Calculate statistics
        total_urls = len(scraped_content)
        successful_scrapes = len([content for content in scraped_content if content.status_code == 200])
        failed_scrapes = total_urls - successful_scrapes
        
        logger.info(f"Scrape-and-chunk completed: {successful_scrapes} URLs scraped, {len(saved_chunks)} chunks generated")
        
        return {
            "message": f"Successfully scraped {successful_scrapes} URLs and generated {len(saved_chunks)} chunks",
            "scraping_stats": {
                "total_urls_scraped": total_urls,
                "successful_scrapes": successful_scrapes,
                "failed_scrapes": failed_scrapes,
                "processing_time_seconds": round(processing_time, 2)
            },
            "chunks_generated": len(saved_chunks),
            "chunks": saved_chunks,
            "scraped_content": [content.model_dump() for content in scraped_content]
        }
        
    except Exception as e:
        logger.error(f"Error in scrape-and-chunk for {request.url}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape and generate chunks: {str(e)}"
        )


