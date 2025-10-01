import os, httpx, json, logging
from app.database_operations import get_supabase_client
from typing import Optional, List

logger = logging.getLogger(__name__)


async def upload_chunk_to_vapi(
    chunk_id: str, 
    chunk_name: str, 
    chunk_content: str, 
    bullets: Optional[List[str]] = None, 
    sample_questions: Optional[List[str]] = None
) -> Optional[str]:
    """
    Upload a chunk as a file to VAPI knowledge base.
    Combines content, bullets, and sample questions into a rich formatted file.
    
    Args:
        chunk_id: UUID of the chunk
        chunk_name: Name/title of the chunk
        chunk_content: The actual content to upload
        bullets: Key bullet points from the content
        sample_questions: Sample questions this chunk can answer
        
    Returns:
        VAPI file ID if successful, None otherwise
    """
    vapi_key = os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
    if not vapi_key:
        logger.warning("VAPI token not configured, skipping file upload")
        return None
    
    try:
        # Format the complete content with all information
        formatted_content_parts = []
        
        # Add title
        formatted_content_parts.append(f"# {chunk_name}\n")
        
        # Add main content
        if chunk_content:
            formatted_content_parts.append(f"## Content\n{chunk_content}\n")
        
        # Add key points/bullets
        if bullets and len(bullets) > 0:
            formatted_content_parts.append("\n## Key Points")
            for bullet in bullets:
                formatted_content_parts.append(f"• {bullet}")
            formatted_content_parts.append("")  # Empty line
        
        # Add sample questions
        if sample_questions and len(sample_questions) > 0:
            formatted_content_parts.append("\n## Common Questions")
            for i, question in enumerate(sample_questions, 1):
                formatted_content_parts.append(f"{i}. {question}")
        
        # Combine all parts
        full_content = "\n".join(formatted_content_parts)
        
        # Upload to VAPI
        async with httpx.AsyncClient(timeout=60) as client:
            files = {
                'file': (f'{chunk_name}.txt', full_content.encode('utf-8'), 'text/plain')
            }
            
            response = await client.post(
                "https://api.vapi.ai/file",
                headers={"Authorization": f"Bearer {vapi_key}"},
                files=files
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                file_id = result.get('id')
                logger.info(f"Successfully uploaded chunk {chunk_id} to VAPI, file_id: {file_id}")
                return file_id
            else:
                logger.error(f"Failed to upload chunk to VAPI: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error uploading chunk to VAPI: {str(e)}")
        return None


async def get_vapi_file_ids_for_receptionist(receptionist_id: str) -> List[str]:
    """Get all VAPI file IDs for chunks belonging to a receptionist."""
    supabase = get_supabase_client()
    res = supabase.table("chunks").select("vapi_file_id").eq("receptionist_id", receptionist_id).execute()
    
    # Filter out None values and return list of file IDs
    file_ids = [row["vapi_file_id"] for row in (res.data or []) if row.get("vapi_file_id")]
    return file_ids


async def build_system_prompt(receptionist_id: str) -> str:
    """Concatenate all chunk content for a receptionist into a single prompt."""
    supabase = get_supabase_client()
    res = supabase.table("chunks").select("content").eq("receptionist_id", receptionist_id).execute()
    contents = [row["content"] for row in (res.data or []) if row.get("content")]
    return "\n\n".join(contents) if contents else "No knowledge available yet."


async def sync_assistant_prompt(assistant_id: str, receptionist_id: str):
    """
    Update VAPI assistant with knowledge base file IDs.
    Uses VAPI's knowledge base feature instead of concatenating content in system prompt.
    """
    vapi_key = os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
    if not vapi_key:
        logger.warning("VAPI token not configured, skipping assistant sync")
        return  # silently skip

    # Get all VAPI file IDs for this receptionist
    file_ids = await get_vapi_file_ids_for_receptionist(receptionist_id)
    
    # Build the payload with knowledgeBase
    system_prompt = """You are an AI Receptionist for this business.
Answer only using the approved Knowledge Base (KB). If a question is outside the KB, politely say you can't help with that question. Be concise, friendly, and solution-oriented.

Core rules:

• KB-only answers: Use facts from the KB verbatim. If something is missing or ambiguous, ask a brief follow-up or offer escalation.

• Out-of-scope: If the question isn't covered by the KB, say you're specialized for this business and can't help with that topic; then suggest contacting support or visiting the website.

• No hallucinations: Do not invent policies, prices, people, dates, or promises.

• Privacy & safety: Don't collect sensitive info beyond what the KB explicitly allows (e.g., name, email, phone). Avoid medical, legal, or financial advice.

• Tone: Warm, professional, brief. Use bullets for steps; avoid long paragraphs.

• Actions: If booking or lead capture is enabled, confirm key details (name, contact, date/time, location) before finalizing.

Formatting:

• Prefer a one-sentence answer when possible.

• For steps, use a short bulleted list (max 5 bullets).

• Put the most important detail first (price, date, deadline, link).

When info is missing:

• If a single detail is missing: ask one targeted question.

• If multiple details are missing: list the needed items compactly, then wait.

Out-of-scope response (template):

"I'm specialized for this business's questions. I can't help with that topic, but you can reach our support team."
"""
    
    payload = {
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "maxTokens": 90,
            "messages": [
                {"role": "system", "content": system_prompt}
            ]
        }
    }
    
    # Add knowledge base if we have file IDs
    if file_ids:
        payload["model"]["knowledgeBase"] = {
            "provider": "canonical",  # VAPI's default provider
            "fileIds": file_ids
        }
        logger.info(f"Syncing assistant {assistant_id} with {len(file_ids)} knowledge base files")
    else:
        logger.info(f"No knowledge base files found for receptionist {receptionist_id}")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(
                f"https://api.vapi.ai/assistant/{assistant_id}",
                headers={"Authorization": f"Bearer {vapi_key}", "Content-Type": "application/json"},
                json=payload,
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully synced assistant {assistant_id}")
            else:
                logger.error(f"Failed to sync assistant: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error syncing assistant: {str(e)}")


def build_assistant_payload(org_name: str, receptionist_name: str, voice_id: str, first_message: str | None = None, **overrides):
    payload = {
        "name": f"{org_name} - {receptionist_name}",
        "voice": {"voiceId": voice_id, "provider": "vapi"},
        "model": {"provider": "openai", "model": "gpt-4o", "maxTokens": 90},
        "firstMessage": first_message or f"Hello! You’re speaking with the AI assistant of {org_name}. How can I assist you today?",
        "voicemailMessage": "Please call back when you're available.",
        "voicemailDetection": {
            "provider": "vapi",
            "backoffPlan": {"maxRetries": 6, "startAtSeconds": 5, "frequencySeconds": 5},
            "beepMaxAwaitSeconds": 1,
        },
        "backgroundDenoisingEnabled": True,
        "startSpeakingPlan": {"waitSeconds": 1, "transcriptionEndpointingPlan": {"onPunctuationSeconds": 0.5}},
        "stopSpeakingPlan": {"numWords": 1, "voiceSeconds": 0.1},
        "endCallMessage": "Goodbye.",
        "transcriber": {"model": "nova-2", "language": "en", "provider": "deepgram"},
    }
    payload.update(overrides)
    return payload
