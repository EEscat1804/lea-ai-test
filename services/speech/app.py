"""
Speech intake service: multilingual ASR + language ID + emotion (SER) + audio
event detection (AED), built on the SenseVoiceSmall model via FunASR.

Model code and weights are not vendored — this service depends on the published
`funasr` package and downloads `iic/SenseVoiceSmall` from ModelScope/Hugging Face
on first run. See README.md for licensing and what was excluded from the source
project (https://github.com/QwenAudio/SenseVoice).

Set SENSEVOICE_DEVICE=cuda:0 (or another CUDA device) to run on GPU; defaults to CPU.

/v1/transcribe requires `Authorization: Bearer <SPEECH_SERVICE_TOKEN>`. The
token must be set via the SPEECH_SERVICE_TOKEN env var — if it isn't set,
the endpoint refuses all requests (fail-closed) rather than running open.
/health is unauthenticated for basic liveness checks.
"""

from __future__ import annotations

import asyncio
import hmac
import os
import re
import threading
from io import BytesIO
from typing import Annotated, Any, TypedDict

import soundfile as sf
import torch
import torchaudio
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

TARGET_FS = 16000
SPEECH_SERVICE_TOKEN = os.getenv("SPEECH_SERVICE_TOKEN")

# Placeholder defaults — no existing size/duration limit signal was found
# elsewhere in this repo. Revisit once real call-audio traffic data exists.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_AUDIO_SECONDS = 10 * 60
ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/x-wav", "audio/wave", "audio/mpeg", "audio/mp3"}
ALLOWED_EXTENSIONS = {".wav", ".mp3"}

# A compressed file decodes into much more raw audio than its byte size
# implies (e.g. an mp3 well under MAX_UPLOAD_BYTES can still decode into
# hours of audio) — MAX_UPLOAD_BYTES alone doesn't bound inference cost.
MAX_CONCURRENT_TRANSCRIPTIONS = int(os.getenv("MAX_CONCURRENT_TRANSCRIPTIONS", "2"))
INFERENCE_QUEUE_TIMEOUT_SECONDS = float(os.getenv("INFERENCE_QUEUE_TIMEOUT_SECONDS", "30"))
_inference_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TRANSCRIPTIONS)

LANGUAGE_TAGS = {"zh", "en", "yue", "ja", "ko", "nospeech"}
EMOTION_TAGS = {
    "HAPPY", "SAD", "ANGRY", "NEUTRAL", "FEARFUL", "DISGUSTED", "SURPRISED", "EMO_UNKNOWN",
}
EVENT_TAGS = {"BGM", "Speech", "Applause", "Laughter", "Cry", "Sneeze", "Breath", "Cough"}
TAG_RE = re.compile(r"<\|([^|]+)\|>")

# Emoji/symbols rich_transcription_postprocess embeds in its output (see
# funasr.utils.postprocess_utils: emo_dict / event_dict values, plus the
# nospeech placeholder) — stripped back out to derive clean_text from the
# *rich* text, rather than re-deriving it independently from raw tags, so
# clean_text can never drift from whatever that function actually produces.
_DECORATIVE_SYMBOLS = "😊😔😡😰🤢😮🎼👏😀😭🤧❓"


class ParsedTags(TypedDict):
    language: str | None
    emotion: str | None
    events: list[str]


def parse_tags(tagged_text: str) -> ParsedTags:
    """Extract structured language/emotion/event fields from a SenseVoice
    tagged string (e.g. "<|en|><|HAPPY|><|Speech|><|withitn|>hello")."""
    language: str | None = None
    emotion: str | None = None
    events: list[str] = []
    for tag in TAG_RE.findall(tagged_text):
        if tag in LANGUAGE_TAGS:
            language = tag
        elif tag in EMOTION_TAGS:
            emotion = tag
        elif tag in EVENT_TAGS:
            events.append(tag)
    return {"language": language, "emotion": emotion, "events": events}


def strip_decorative_symbols(rich_text: str) -> str:
    """Derive a plain-text transcript from rich_transcription_postprocess's
    output by removing the emoji/symbols it embeds."""
    return "".join(ch for ch in rich_text if ch not in _DECORATIVE_SYMBOLS).strip()


def load_audio(raw_bytes: bytes) -> torch.Tensor:
    # soundfile (libsndfile) instead of torchaudio.load: the installed
    # torchaudio build routes .load() through torchcodec, which needs a
    # system FFmpeg install we don't want as a hard requirement here.
    data, sample_rate = sf.read(BytesIO(raw_bytes), dtype="float32", always_2d=True)
    waveform = torch.from_numpy(data.T)  # (channels, samples)
    if sample_rate != TARGET_FS:
        resample = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=TARGET_FS)
        waveform = resample(waveform)
    return torch.Tensor(waveform.mean(0))


_model: AutoModel | None = None
_model_lock = threading.Lock()


def get_model() -> AutoModel:
    """Lazily construct the model on first use (not at import time, and not
    at request-dependency-resolution time either — see the call site in
    _transcribe_sync). Monkeypatchable at module level in tests."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = AutoModel(
                    model="iic/SenseVoiceSmall",
                    vad_model="fsmn-vad",
                    vad_kwargs={"max_single_segment_time": 30000},
                    device=os.getenv("SENSEVOICE_DEVICE", "cpu"),
                )
    return _model


def _transcribe_sync(raw_bytes: bytes, language: str, use_itn: bool) -> list[dict[str, Any]]:
    """Blocking work (audio decode + model inference) — run via run_in_threadpool
    so it doesn't tie up the async event loop for the duration of a request.

    get_model() is called here — inside the thread, after decode + duration
    validation — rather than as a FastAPI route dependency. A Depends()
    parameter is resolved before the handler body runs, which would
    construct/load the model for every request (including ones that fail
    file-type or size validation) before that validation ever executes.
    """
    audio = load_audio(raw_bytes)
    duration_seconds = audio.shape[-1] / TARGET_FS
    if duration_seconds > MAX_AUDIO_SECONDS:
        raise AudioTooLongError(duration_seconds)
    model = get_model()
    result: list[dict[str, Any]] = model.generate(
        input=audio,
        cache={},
        language=language,
        use_itn=use_itn,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )
    return result


class AudioTooLongError(Exception):
    def __init__(self, duration_seconds: float) -> None:
        self.duration_seconds = duration_seconds
        message = f"audio duration {duration_seconds:.1f}s exceeds {MAX_AUDIO_SECONDS}s limit"
        super().__init__(message)


app = FastAPI(title="LEA Speech Intake Service")


async def require_auth(authorization: Annotated[str | None, Header()] = None) -> None:
    if not SPEECH_SERVICE_TOKEN:
        raise HTTPException(status_code=503, detail="SPEECH_SERVICE_TOKEN is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(token, SPEECH_SERVICE_TOKEN):
        raise HTTPException(status_code=401, detail="invalid token")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/transcribe", dependencies=[Depends(require_auth)])
async def transcribe(
    file: Annotated[UploadFile, File(description="wav or mp3 audio, any duration")],
    language: str = "auto",
    use_itn: bool = True,
) -> dict[str, Any]:
    extension = os.path.splitext(file.filename or "")[1].lower()
    if file.content_type not in ALLOWED_CONTENT_TYPES and extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"unsupported file type (content_type={file.content_type!r}, "
                f"filename={file.filename!r}); expected wav or mp3"
            ),
        )

    raw_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"file exceeds {limit_mb}MB limit")

    try:
        await asyncio.wait_for(
            _inference_semaphore.acquire(), timeout=INFERENCE_QUEUE_TIMEOUT_SECONDS
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail="server busy, try again later") from exc

    try:
        result = await run_in_threadpool(_transcribe_sync, raw_bytes, language, use_itn)
    except sf.LibsndfileError as exc:
        # bad/corrupt/undecodable audio is the caller's fault, not a server error
        raise HTTPException(status_code=400, detail=f"could not decode audio: {exc}") from exc
    except AudioTooLongError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    finally:
        _inference_semaphore.release()

    if not result:
        return JSONResponse({"error": "no speech detected"}, status_code=422)  # type: ignore[return-value]

    item = result[0]
    tags = parse_tags(item["text"])
    rich_text = rich_transcription_postprocess(item["text"])

    segments: list[dict[str, Any]] = []
    for sentence in item.get("sentence_info", []):
        sentence_tags = parse_tags(sentence["text"])
        sentence_rich_text = rich_transcription_postprocess(sentence["text"])
        segments.append(
            {
                "start_ms": sentence.get("start"),
                "end_ms": sentence.get("end"),
                "text": sentence_rich_text,
                "clean_text": strip_decorative_symbols(sentence_rich_text),
                **sentence_tags,
            }
        )

    return {
        "text": rich_text,
        "clean_text": strip_decorative_symbols(rich_text),
        "language": tags["language"],
        "emotion": tags["emotion"],
        "events": tags["events"],
        "segments": segments,
    }


if __name__ == "__main__":
    import uvicorn

    # Intentional bind-all: this is the container entrypoint, not exposed
    # directly — see Dockerfile / README for the deployment model.
    uvicorn.run(app, host=os.getenv("SPEECH_SERVICE_HOST", "0.0.0.0"), port=50000)  # noqa: S104
