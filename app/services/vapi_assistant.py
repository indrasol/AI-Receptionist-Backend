import os, httpx
from app.database_operations import get_supabase_client


async def build_system_prompt(receptionist_id: str) -> str:
    """Concatenate all chunk content for a receptionist into a single prompt."""
    supabase = get_supabase_client()
    res = supabase.table("chunks").select("content").eq("receptionist_id", receptionist_id).execute()
    contents = [row["content"] for row in (res.data or []) if row.get("content")]
    return "\n\n".join(contents) if contents else "No knowledge available yet."


async def sync_assistant_prompt(assistant_id: str, receptionist_id: str):
    """Update Vapi assistant with combined system prompt from chunks."""
    prompt = await build_system_prompt(receptionist_id)
    vapi_key = os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
    if not vapi_key:
        return  # silently skip

    payload = {
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "maxTokens": 90,
            "messages": [
                {"role": "system", "content": prompt}
            ]
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        await client.patch(
            f"https://api.vapi.ai/assistant/{assistant_id}",
            headers={"Authorization": f"Bearer {vapi_key}", "Content-Type": "application/json"},
            json=payload,
        )


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
