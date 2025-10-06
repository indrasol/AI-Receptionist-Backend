"""Utility for sending transactional emails via Supabase Edge Function.

Assumes you have deployed an Edge Function named `send-mail` that accepts JSON
{ "to": "user@example.com", "subject": "...", "body": "..." }

The backend invokes it with the Supabase service-role key so it won't be rate-
limited. Nothing in this utility exposes the key to the client.
"""

import logging
import httpx
from app.config.settings import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, EMAIL_FROM

logger = logging.getLogger(__name__)

async def send_email_async(to_email: str, subject: str, body: str):
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        logger.warning("Supabase credentials not configured; cannot send email")
        return

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": to_email,
        "subject": subject,
        "body": body,
        "from": EMAIL_FROM or "no-reply@aireceptionist.app",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{SUPABASE_URL}/functions/v1/send-mail", json=payload, headers=headers)
            resp.raise_for_status()
        logger.info("Sent email via Supabase Edge Function → %s", to_email)
    except Exception as exc:
        logger.error("Failed to call Supabase send-mail function: %s", exc)
