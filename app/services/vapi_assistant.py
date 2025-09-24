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
