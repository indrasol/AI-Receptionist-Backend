"""
URL Scraping API Endpoints
Handles web scraping requests and content extraction
"""

from fastapi import APIRouter, HTTPException, Depends, Query
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
    """Enqueue a background scrape job and return its task_id."""

    try:
        # Identify org / receptionist
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")

        supabase = get_supabase_client()

        # Create task row in DB
        task_row = {
            "status": "queued",
            "url": request.url,
            "organization_id": organization_id,
            "receptionist_id": request.receptionist_id,
        }
        inserted = supabase.table("scrape_tasks").insert(task_row).execute()
        task_id = inserted.data[0]["id"]

        # Enqueue Celery task (include notify_email from current user)
        from app.tasks.scrape_tasks import scrape_website
        scrape_website.delay(
            task_id=task_id,
            url=request.url,
            receptionist_id=request.receptionist_id,
            organization_id=str(organization_id),
            max_depth=request.max_depth or 3,
            include_subdomains=request.include_subdomains if request.include_subdomains is not None else True,
            include_subpages=request.include_subpages if request.include_subpages is not None else True,
            notify_email=current_user.get("email"),
        )

        return {"task_id": task_id, "status": "queued"}
    except Exception as e:
        logger.error(f"Failed to enqueue scrape: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue scrape task")


# ---------------- New endpoints -----------------


@router.get("/task/{task_id}")
async def get_scrape_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Return status information for a specific scrape task."""
    supabase = get_supabase_client()
    resp = supabase.table("scrape_tasks").select("*").eq("id", task_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="task not found")
    return resp.data


@router.delete("/task/{task_id}")
async def delete_scrape_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a scrape task and clean up Redis logs."""
    try:
        supabase = get_supabase_client()
        
        # Check if task exists and belongs to user's organization
        resp = supabase.table("scrape_tasks").select("*").eq("id", task_id).single().execute()
        if not resp.data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        organization_id = current_user.get("organization", {}).get("id")
        if resp.data.get("organization_id") != organization_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this task")
        
        # Delete from database
        supabase.table("scrape_tasks").delete().eq("id", task_id).execute()
        
        # Clean up Redis logs
        try:
            import redis
            from app.config.settings import REDIS_URL
            r = redis.from_url(REDIS_URL)
            channel = f"scrape:{task_id}"
            # Remove the log list
            r.delete(f"{channel}:log")
            logger.info(f"Cleaned up Redis logs for task {task_id}")
        except Exception as redis_error:
            logger.warning(f"Failed to clean up Redis logs: {redis_error}")
        
        return {"message": f"Task {task_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete task")


@router.get("/active-task")
async def get_active_task(
    receptionist_id: str = Query(None, description="Filter by receptionist"),
    current_user: dict = Depends(get_current_user),
):
    """Return the most recent task in queued/in_progress for org or receptionist."""
    organization_id = current_user.get("organization", {}).get("id")
    if not organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    supabase = get_supabase_client()
    q = (
        supabase.table("scrape_tasks")
        .select("*")
        .eq("organization_id", organization_id)
        .in_("status", ["queued", "in_progress"])
        .order("created_at", desc=True)
        .limit(1)
    )
    if receptionist_id:
        q = q.eq("receptionist_id", receptionist_id)
    resp = q.execute()
    if resp.data:
        return resp.data[0]
    return {"status": "idle"}


