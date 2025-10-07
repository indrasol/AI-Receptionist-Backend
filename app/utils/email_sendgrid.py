import logging
from typing import Dict, Any, Optional

import httpx

from app.config.settings import (
    EMAIL_FROM,
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL,
    SENDGRID_TEMPLATE_SCRAPE_COMPLETE,
    BRAND_NAME,
    BRAND_LOGO_URL,
    BRAND_PRIMARY_COLOR,
)

logger = logging.getLogger(__name__)


async def send_sendgrid_template_email(
    to_email: str,
    template_id: Optional[str],
    dynamic_template_data: Dict[str, Any],
    from_email: Optional[str] = None,
):
    """Send an email via SendGrid Dynamic Template API using httpx.

    Args:
        to_email: Recipient email address
        template_id: SendGrid dynamic template ID
        dynamic_template_data: Variables for the template
        from_email: Optional override for the sender email
    """

    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not configured; skipping email send to %s", to_email)
        return

    resolved_from = from_email or SENDGRID_FROM_EMAIL or EMAIL_FROM
    if not resolved_from:
        logger.warning("Sender email not configured; skipping email send to %s", to_email)
        return

    if not template_id:
        logger.warning("SendGrid template_id missing; skipping email send to %s", to_email)
        return

    # Ensure brand defaults are present unless explicitly provided
    if "brand_name" not in dynamic_template_data:
        dynamic_template_data["brand_name"] = BRAND_NAME
    if "brand_logo_url" not in dynamic_template_data and BRAND_LOGO_URL:
        dynamic_template_data["brand_logo_url"] = BRAND_LOGO_URL
    if "primary_color" not in dynamic_template_data and BRAND_PRIMARY_COLOR:
        dynamic_template_data["primary_color"] = BRAND_PRIMARY_COLOR

    payload = {
        "from": {"email": resolved_from},
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "dynamic_template_data": dynamic_template_data,
            }
        ],
        "template_id": template_id,
    }

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers)
            resp.raise_for_status()
        logger.info("SendGrid email enqueued → %s template=%s", to_email, template_id)
    except Exception as exc:
        logger.error("SendGrid send failed for %s: %s", to_email, exc)


async def send_scrape_complete_email(to_email: str, context: Dict[str, Any]):
    """Convenience wrapper for the scrape completion template."""
    await send_sendgrid_template_email(
        to_email=to_email,
        template_id=SENDGRID_TEMPLATE_SCRAPE_COMPLETE,
        dynamic_template_data=context,
    )


