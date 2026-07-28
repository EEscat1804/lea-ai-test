"""
Minimal pytest suite for services/speech, scoped to this service only.

Uses FastAPI's TestClient (in-process, no separate server process needed).
The model is loaded lazily (see app.get_model) — importing this module and
running the auth/validation tests below does NOT download or load the real
model. Only tests marked @pytest.mark.integration touch the real model and
need network access on first run; run everything else with:

    pytest tests/ -m "not integration"

Run from services/speech/:  pytest tests/
Requires: pip install -r requirements.txt -r requirements-dev.txt
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("SPEECH_SERVICE_TOKEN", "test-token-for-pytest")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app import app, get_model
from fastapi.testclient import TestClient

client = TestClient(app)
FIXTURES = Path(__file__).resolve().parent / "fixtures"
AUTH = {"Authorization": f"Bearer {os.environ['SPEECH_SERVICE_TOKEN']}"}


class FakeModel:
    """Stand-in for funasr's AutoModel, injected via app.dependency_overrides
    so response-shaping logic (tag parsing, clean_text symbol stripping) can
    be tested deterministically without the real model or network access."""

    def __init__(self, tagged_text: str) -> None:
        self.tagged_text = tagged_text

    def generate(self, **_kwargs: Any) -> list[dict[str, Any]]:
        return [{"key": "fake", "text": self.tagged_text, "sentence_info": []}]


def test_health_requires_no_auth() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_transcribe_rejects_missing_auth() -> None:
    with open(FIXTURES / "trigger_weapon.wav", "rb") as f:
        r = client.post("/v1/transcribe", files={"file": ("trigger_weapon.wav", f, "audio/wav")})
    assert r.status_code == 401


def test_transcribe_rejects_wrong_auth() -> None:
    with open(FIXTURES / "trigger_weapon.wav", "rb") as f:
        r = client.post(
            "/v1/transcribe",
            files={"file": ("trigger_weapon.wav", f, "audio/wav")},
            headers={"Authorization": "Bearer wrong-token"},
        )
    assert r.status_code == 401


def test_transcribe_rejects_wrong_file_type() -> None:
    r = client.post(
        "/v1/transcribe",
        files={"file": ("notaudio.txt", b"not audio", "text/plain")},
        headers=AUTH,
    )
    assert r.status_code == 400


def test_transcribe_rejects_undecodable_audio() -> None:
    r = client.post(
        "/v1/transcribe",
        files={"file": ("bad.wav", b"garbage bytes, not real audio", "audio/wav")},
        headers=AUTH,
    )
    assert r.status_code == 400


def test_transcribe_rejects_oversized_file() -> None:
    oversized = b"0" * (25 * 1024 * 1024 + 1)
    r = client.post(
        "/v1/transcribe",
        files={"file": ("big.wav", oversized, "audio/wav")},
        headers=AUTH,
    )
    assert r.status_code == 413


def test_transcribe_clean_text_strips_emoji_from_fake_model() -> None:
    """Regression test for the bug where clean_text could retain the emoji
    rich_transcription_postprocess embeds for a recognized emotion. Uses a
    HAPPY tag specifically because it's the case that previously wasn't
    exercised by any real-audio fixture (trigger_weapon.wav reports
    EMO_UNKNOWN, which maps to no emoji at all)."""
    app.dependency_overrides[get_model] = lambda: FakeModel(
        "<|en|><|HAPPY|><|Speech|><|withitn|>I am so happy today"
    )
    try:
        with open(FIXTURES / "trigger_weapon.wav", "rb") as f:
            files = {"file": ("trigger_weapon.wav", f, "audio/wav")}
            r = client.post("/v1/transcribe", files=files, headers=AUTH)
    finally:
        app.dependency_overrides.pop(get_model, None)

    assert r.status_code == 200
    body = r.json()
    assert "😊" in body["text"]
    assert "😊" not in body["clean_text"]
    assert body["emotion"] == "HAPPY"
    assert body["language"] == "en"


@pytest.mark.integration
def test_transcribe_wav_end_to_end() -> None:
    with open(FIXTURES / "trigger_weapon.wav", "rb") as f:
        files = {"file": ("trigger_weapon.wav", f, "audio/wav")}
        r = client.post("/v1/transcribe", files=files, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "en"
    assert "weapon" in body["clean_text"].lower()


@pytest.mark.integration
def test_transcribe_mp3_input() -> None:
    with open(FIXTURES / "sample_en.mp3", "rb") as f:
        files = {"file": ("sample_en.mp3", f, "audio/mpeg")}
        r = client.post("/v1/transcribe", files=files, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["clean_text"]  # non-empty transcript
