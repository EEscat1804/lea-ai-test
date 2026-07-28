"""
Lightweight HTTP client for the speech intake service, for use by the main
Lea AI app (which shouldn't need torch/funasr as a direct dependency just to
send an audio file to this service).
"""

import os

import requests


def transcribe(
    audio_path: str,
    service_url: str = "http://localhost:50000",
    language: str = "auto",
    token: str = None,
) -> dict:
    """POST an audio file to the speech service and return its parsed JSON response.

    token defaults to the SPEECH_SERVICE_TOKEN env var (same variable the
    service itself reads) so callers don't need to pass it explicitly in the
    common case of client and service sharing one deployment config.
    """
    token = token or os.getenv("SPEECH_SERVICE_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with open(audio_path, "rb") as f:
        response = requests.post(
            f"{service_url}/v1/transcribe",
            files={"file": f},
            params={"language": language},
            headers=headers,
            timeout=60,
        )
    response.raise_for_status()
    return response.json()
