"""
Minimal pytest suite for services/speech, scoped to this service only.

Uses FastAPI's TestClient (in-process, no separate server process needed),
which also means app.py's model is loaded once per test session.

Run from services/speech/:  pytest tests/
Requires: pip install -r requirements.txt -r requirements-dev.txt
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("SPEECH_SERVICE_TOKEN", "test-token-for-pytest")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

client = TestClient(app)
FIXTURES = Path(__file__).resolve().parent / "fixtures"
AUTH = {"Authorization": f"Bearer {os.environ['SPEECH_SERVICE_TOKEN']}"}


def test_health_requires_no_auth():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_transcribe_rejects_missing_auth():
    with open(FIXTURES / "trigger_weapon.wav", "rb") as f:
        r = client.post("/v1/transcribe", files={"file": ("trigger_weapon.wav", f, "audio/wav")})
    assert r.status_code == 401


def test_transcribe_rejects_wrong_auth():
    with open(FIXTURES / "trigger_weapon.wav", "rb") as f:
        r = client.post(
            "/v1/transcribe",
            files={"file": ("trigger_weapon.wav", f, "audio/wav")},
            headers={"Authorization": "Bearer wrong-token"},
        )
    assert r.status_code == 401


def test_transcribe_rejects_wrong_file_type():
    r = client.post(
        "/v1/transcribe",
        files={"file": ("notaudio.txt", b"not audio", "text/plain")},
        headers=AUTH,
    )
    assert r.status_code == 400


def test_transcribe_rejects_undecodable_audio():
    r = client.post(
        "/v1/transcribe",
        files={"file": ("bad.wav", b"garbage bytes, not real audio", "audio/wav")},
        headers=AUTH,
    )
    assert r.status_code == 400


def test_transcribe_rejects_oversized_file():
    oversized = b"0" * (25 * 1024 * 1024 + 1)
    r = client.post(
        "/v1/transcribe",
        files={"file": ("big.wav", oversized, "audio/wav")},
        headers=AUTH,
    )
    assert r.status_code == 413


def test_transcribe_wav_end_to_end():
    with open(FIXTURES / "trigger_weapon.wav", "rb") as f:
        r = client.post("/v1/transcribe", files={"file": ("trigger_weapon.wav", f, "audio/wav")}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "en"
    assert "weapon" in body["clean_text"].lower()


def test_transcribe_mp3_input():
    with open(FIXTURES / "sample_en.mp3", "rb") as f:
        r = client.post("/v1/transcribe", files={"file": ("sample_en.mp3", f, "audio/mpeg")}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["clean_text"]  # non-empty transcript
