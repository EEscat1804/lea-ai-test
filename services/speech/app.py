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

import hmac
import os
import re
from io import BytesIO

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

# Placeholder default — no existing size/duration limit signal was found
# elsewhere in this repo (grepped guardrail spec, feature standard, cultural
# context docs). Revisit once real call-audio traffic/duration data exists.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/x-wav", "audio/wave", "audio/mpeg", "audio/mp3"}
ALLOWED_EXTENSIONS = {".wav", ".mp3"}

LANGUAGE_TAGS = {"zh", "en", "yue", "ja", "ko", "nospeech"}
EMOTION_TAGS = {
    "HAPPY", "SAD", "ANGRY", "NEUTRAL", "FEARFUL", "DISGUSTED", "SURPRISED", "EMO_UNKNOWN",
}
EVENT_TAGS = {"BGM", "Speech", "Applause", "Laughter", "Cry", "Sneeze", "Breath", "Cough"}

TAG_RE = re.compile(r"<\|([^|]+)\|>")

app = FastAPI(title="LEA Speech Intake Service")

model = AutoModel(
    model="iic/SenseVoiceSmall",
    vad_model="fsmn-vad",
    vad_kwargs={"max_single_segment_time": 30000},
    device=os.getenv("SENSEVOICE_DEVICE", "cpu"),
)


def parse_tags(tagged_text: str) -> dict:
    """Split a SenseVoice tagged string into structured fields + clean text."""
    language = None
    emotion = None
    events = []
    for tag in TAG_RE.findall(tagged_text):
        if tag in LANGUAGE_TAGS:
            language = tag
        elif tag in EMOTION_TAGS:
            emotion = tag
        elif tag in EVENT_TAGS:
            events.append(tag)
    clean_text = TAG_RE.sub("", tagged_text).strip()
    return {"language": language, "emotion": emotion, "events": events, "clean_text": clean_text}


def load_audio(raw_bytes: bytes):
    # soundfile (libsndfile) instead of torchaudio.load: the installed
    # torchaudio build routes .load() through torchcodec, which needs a
    # system FFmpeg install we don't want as a hard requirement here.
    data, sample_rate = sf.read(BytesIO(raw_bytes), dtype="float32", always_2d=True)
    waveform = torch.from_numpy(data.T)  # (channels, samples)
    if sample_rate != TARGET_FS:
        waveform = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=TARGET_FS)(waveform)
    return waveform.mean(0)


def _transcribe_sync(raw_bytes: bytes, language: str, use_itn: bool):
    """Blocking work (audio decode + model inference) — run via run_in_threadpool
    so it doesn't tie up the async event loop for the duration of a request."""
    audio = load_audio(raw_bytes)
    return model.generate(
        input=audio,
        cache={},
        language=language,
        use_itn=use_itn,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )


async def require_auth(authorization: str = Header(default=None)):
    if not SPEECH_SERVICE_TOKEN:
        raise HTTPException(status_code=503, detail="SPEECH_SERVICE_TOKEN is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(token, SPEECH_SERVICE_TOKEN):
        raise HTTPException(status_code=401, detail="invalid token")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/transcribe", dependencies=[Depends(require_auth)])
async def transcribe(
    file: UploadFile = File(..., description="wav or mp3 audio, any duration"),
    language: str = "auto",
    use_itn: bool = True,
):
    extension = os.path.splitext(file.filename or "")[1].lower()
    if file.content_type not in ALLOWED_CONTENT_TYPES and extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported file type (content_type={file.content_type!r}, filename={file.filename!r}); expected wav or mp3",
        )

    raw_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"file exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")

    try:
        result = await run_in_threadpool(_transcribe_sync, raw_bytes, language, use_itn)
    except sf.LibsndfileError as exc:
        # bad/corrupt/undecodable audio is the caller's fault, not a server error
        raise HTTPException(status_code=400, detail=f"could not decode audio: {exc}") from exc

    if not result:
        return JSONResponse({"error": "no speech detected"}, status_code=422)

    item = result[0]
    parsed = parse_tags(item["text"])

    segments = []
    for sentence in item.get("sentence_info", []):
        sentence_parsed = parse_tags(sentence["text"])
        segments.append(
            {
                "start_ms": sentence.get("start"),
                "end_ms": sentence.get("end"),
                "text": rich_transcription_postprocess(sentence["text"]),
                **sentence_parsed,
            }
        )

    return {
        "text": rich_transcription_postprocess(item["text"]),
        "clean_text": parsed["clean_text"],
        "language": parsed["language"],
        "emotion": parsed["emotion"],
        "events": parsed["events"],
        "segments": segments,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=50000)
