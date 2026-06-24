"""
ElevenLabs Speech-to-Text — converts caller audio to text.

Uses the ElevenLabs STT API to transcribe audio from Twilio media streams.
Twilio sends audio as base64-encoded μ-law 8kHz mono.
"""

import logging

import httpx
from control.voice.voice_config import voice_config

logger = logging.getLogger(__name__)

# ElevenLabs STT endpoint
STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"


async def speech_to_text(audio_bytes: bytes) -> str:
    """
    Transcribe audio bytes using ElevenLabs STT API.

    Args:
        audio_bytes: Raw audio data (μ-law 8kHz from Twilio).

    Returns:
        Transcribed text string.
    """
    headers = {
        "xi-api-key": voice_config.elevenlabs_api_key,
    }

    # Send as multipart form with audio file
    files = {
        "file": ("audio.wav", audio_bytes, "audio/basic"),
    }

    data = {
        "model_id": "scribe_v1",  # ElevenLabs Scribe STT model
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            STT_URL,
            headers=headers,
            files=files,
            data=data,
        )

        if response.status_code != 200:
            logger.error(
                f"ElevenLabs STT error: {response.status_code} — {response.text[:200]}"
            )
            return ""

        result = response.json()
        text = result.get("text", "").strip()

        logger.info(f"[STT] Transcribed: {text[:100]}")
        return text
