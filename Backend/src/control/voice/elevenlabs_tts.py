"""
ElevenLabs Text-to-Speech — converts agent text responses to audio.

Returns raw audio bytes (μ-law 8kHz) suitable for Twilio phone calls.
"""

import logging

import httpx
from control.voice.voice_config import voice_config

logger = logging.getLogger(__name__)

# ElevenLabs TTS endpoint
TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"


async def text_to_speech(text: str) -> bytes:
    """
    Convert text to speech using ElevenLabs API.

    Returns audio bytes in MP3 format (Twilio <Play> compatible).
    """
    url = TTS_URL.format(voice_id=voice_config.elevenlabs_voice_id)

    headers = {
        "xi-api-key": voice_config.elevenlabs_api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": voice_config.elevenlabs_model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
        "output_format": "mp3_44100_128",  # MP3 for Twilio <Play>
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error(
                f"ElevenLabs TTS error: {response.status_code} — {response.text[:200]}"
            )
            raise RuntimeError(f"ElevenLabs TTS failed: {response.status_code}")

        return response.content


async def text_to_speech_streaming(text: str):
    """
    Stream TTS audio chunks from ElevenLabs.

    Yields audio chunks as they arrive — useful for reducing latency
    on longer responses.
    """
    url = TTS_URL.format(voice_id=voice_config.elevenlabs_voice_id)

    headers = {
        "xi-api-key": voice_config.elevenlabs_api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": voice_config.elevenlabs_model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
        "output_format": "mp3_44100_128",  # MP3 for Twilio <Play>
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                error_body = await resp.aread()
                logger.error(
                    f"ElevenLabs TTS stream error: {resp.status_code} — {error_body[:200]}"
                )
                raise RuntimeError(f"ElevenLabs TTS failed: {resp.status_code}")

            async for chunk in resp.aiter_bytes(chunk_size=1024):
                if chunk:
                    yield chunk
