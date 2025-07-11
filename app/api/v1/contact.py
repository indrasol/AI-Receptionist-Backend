from fastapi import APIRouter
from app.schemas.contact import ContactForm, ContactResponse
import logging
import httpx
from app.database import get_supabase_client
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ContactResponse)
async def contact_handler(form: ContactForm):
    """
    Simple contact form handler that prints to console and returns the data
    """
    # Print to console
    print("=" * 50)
    print("NEW CONTACT FORM SUBMISSION")
    print("=" * 50)
    print(f"Name: {form.name}")
    print(f"Email: {form.email}")
    print(f"Company: {form.company or 'N/A'}")
    print(f"Subject: {form.subject or 'N/A'}")
    print(f"Message: {form.message or 'N/A'}")
    print(f"Channel: ['teams']")
    print("=" * 50)
    
    # Send Teams notification
    try:
        # Determine webhook URL based on environment
        if settings.debug:
            webhook_url = "https://webhookbot.c-toss.com/api/bot/webhooks/e0f4c984-7840-45d7-bb76-743a77220cfe"
        else:
            webhook_url = "https://webhookbot.c-toss.com/api/bot/webhooks/54e17e63-63b3-488b-96c4-5a155f9152f5"
        
        # Create Teams message
        teams_message_parts = [
            "🚨 **New Inquiry in AI Receptionist**",
            "",
            f"**Name:** {form.name}",
            f"**Email:** {form.email}"
        ]
        
        if form.company:
            teams_message_parts.append(f"**Company:** {form.company}")
        
        if form.subject:
            teams_message_parts.append(f"**Subject:** {form.subject}")
        
        if form.message:
            teams_message_parts.append(f"**Message:** {form.message}")
        
        teams_message = "<br>".join(teams_message_parts)
        
        # Send to Teams
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json={"text": teams_message},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        
        logger.info(f"Teams notification sent successfully for {form.name} ({form.email})")
        print(f"✅ Teams notification sent successfully")
    except Exception as e:
        logger.error(f"Failed to send Teams notification: {e}")
        print(f"❌ Error sending Teams notification: {e}")
    
    # Save to Supabase
    try:
        supabase = get_supabase_client()
        
        # Determine table name based on environment
        table_name = "ai_receptionist_reach_dev" if settings.debug else "ai_receptionist_reach"
        
        data = {
            "name": form.name,
            "email": form.email,
            "company": form.company,
            "subject": form.subject,
            "message": form.message,
            "channel": ["teams"],
        }
        result = supabase.table(table_name).insert(data).execute()
        logger.info(f"Contact saved to Supabase table '{table_name}': {form.name} ({form.email})")
        print(f"✅ Contact saved to Supabase table '{table_name}' with ID: {result.data[0]['id']}")
    except Exception as e:
        logger.error(f"Failed to save contact to Supabase: {e}")
        print(f"❌ Error saving to Supabase: {e}")
    
    # Also log it
    logger.info(f"Contact form submitted by {form.name} ({form.email})")
    
    return ContactResponse(detail="Contact form submitted successfully") 