from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from app.celery_app import celery_app
from app.services.scraper_service import WebScraperService
from app.services.openai_service import OpenAIService
from app.database_operations import get_supabase_client
from app.services.vapi_assistant import upload_chunk_to_vapi, sync_assistant_prompt

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="app.tasks.scrape_tasks.scrape_website", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def scrape_website(self, task_id: str, url: str, receptionist_id: str | None, organization_id: str, max_depth: int = 3,
                   include_subdomains: bool = True, include_subpages: bool = True) -> dict:
    """Background Celery task that performs full scrape + chunk pipeline."""

    start_ts = datetime.utcnow().isoformat()
    supabase = get_supabase_client()

    # update task row status -> in_progress
    supabase.table("scrape_tasks").update({"status": "in_progress", "started_at": start_ts}).eq("id", task_id).execute()

    scraped_content: List = []
    saved_chunks: List = []
    try:
        # Publish log helper
        def publish(event: str):
            import redis
            from app.config.settings import REDIS_URL
            r = redis.from_url(REDIS_URL)
            channel = f"scrape:{task_id}"
            r.publish(channel, event)
            # also persist so UI can catch up after refresh
            r.rpush(f"{channel}:log", event)

        publish(f"Starting scrape of {url}")
        # Scrape
        import asyncio
        async def run_scrape():
            async with WebScraperService(use_playwright=True) as scraper:
                return await scraper.scrape_url_recursive(
                    url=url,
                    max_depth=max_depth,
                    include_subdomains=include_subdomains,
                    include_subpages=include_subpages,
                )
        scraped_content.extend(asyncio.run(run_scrape()))
        publish("Scraping done, generating chunks…")

        # Generate chunks
        openai_service = OpenAIService()
        chunks = asyncio.run(openai_service.generate_chunks_from_scraped_data(
            scraped_data={"scraped_content": [c.model_dump() for c in scraped_content]},
            organization_id=str(organization_id),
        ))
        if chunks:
            for chunk in chunks:
                chunk["created_by_user_id"] = None
                chunk["receptionist_id"] = receptionist_id

            res = supabase.table("chunks").insert(chunks).execute()
            saved_chunks = res.data or []

        publish(f"Uploading {len(saved_chunks)} chunks to VAPI …")
        for saved_chunk in saved_chunks:
            try:
                cid = saved_chunk["id"]
                vapi_file_id = asyncio.run(upload_chunk_to_vapi(
                    cid,
                    saved_chunk.get("name", "Unnamed Chunk"),
                    saved_chunk.get("content", ""),
                    bullets=saved_chunk.get("bullets", []),
                    sample_questions=saved_chunk.get("sample_questions", []),
                ))
                if vapi_file_id:
                    supabase.table("chunks").update({"vapi_file_id": vapi_file_id}).eq("id", cid).execute()
            except Exception as exc:
                logger.warning(f"Upload chunk failed: {exc}")

        if receptionist_id:
            rec = supabase.table("receptionists").select("assistant_id").eq("id", receptionist_id).single().execute()
            assistant_id = rec.data.get("assistant_id") if rec.data else None
            if assistant_id:
                asyncio.run(sync_assistant_prompt(assistant_id, receptionist_id))

        publish("Scrape finished successfully")

        # Send completion email
        try:
            from app.utils.email_utils import send_email_async
            # lookup user email owning task
            creator_resp = supabase.table("users").select("email").eq("id", self.request.get("args")[0] if False else "").execute()
        except Exception:
            pass  # placeholder

        supabase.table("scrape_tasks").update({"status": "completed", "completed_at": datetime.utcnow().isoformat()}).eq("id", task_id).execute()
        return {"chunks": len(saved_chunks)}
    except Exception as exc:
        logger.exception("Scrape failed")
        supabase.table("scrape_tasks").update({"status": "failed", "error": str(exc)}).eq("id", task_id).execute()
        raise
