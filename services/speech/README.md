# Speech Intake Service (proposal — see PR)

**This is not a Cloudflare Worker component and is not wired into anything
else in this repo.** `lea-ai`'s `CLAUDE.md` is explicit: *"Don't pull in
heavyweight Python deps — Pyodide on Workers has a curated package list.
Many native-extension libs do not work."* This service depends on `torch`
and `funasr` (real PyTorch, native extensions) — it cannot run on Pyodide
and is not part of `requirements.txt`, `wrangler.jsonc`, or `src/worker.py`.
It only builds and runs as its own Docker container, deployed separately,
and would be called over HTTP the same way `lea-be-core` proxies to Gemini
Live rather than embedding it. See the PR this shipped in for the reasoning
and open questions — this folder is a proposal for review, not a merged
integration.

A standalone microservice for multilingual speech-to-text with language ID,
emotion, and audio-event tags on caller audio — built on the [SenseVoiceSmall]
model from [QwenAudio/SenseVoice](https://github.com/QwenAudio/SenseVoice)
(part of the FunAudioLLM family). Potential use: batch/file-based
transcription with an emotion signal (e.g. `FEARFUL`, `ANGRY`) as an input to
guardrails classification — distinct from `lea-be-core`'s existing real-time
`voice_chat` feature (Gemini Live, live bidirectional streaming); this is a
different use case (upload a clip, get a transcript + tags back), not a
replacement for it.

[SenseVoiceSmall]: https://huggingface.co/FunAudioLLM/SenseVoiceSmall

## Audit summary

The upstream repo is mostly training/finetuning tooling (`finetune.sh`,
`deepspeed_conf/`, `data/`), demo scripts, and a WebUI — none of that is
useful for a production intake path. The only thing worth reusing is the
*pattern*: load `iic/SenseVoiceSmall` through the published `funasr` pip
package (Apache-2.0) and call `AutoModel.generate(...)`. Nothing from the
source repo is vendored/copied — `model.py`, `api.py`, etc. stayed upstream.
This service (`app.py`) is a new, minimal FastAPI wrapper around that library
call, adapted from the pattern in the upstream `api.py`/README to:
- use VAD (`fsmn-vad`) so calls longer than 30s work, not just short clips
- return structured `language` / `emotion` / `events` fields (parsed from the
  model's `<|tag|>` output) instead of just raw text
- return per-segment breakdown (`segments`) with timestamps, so a distress
  spike can be located within a call, not just flagged for the whole clip

**Excluded, and why:**
- Training/finetuning scripts, benchmark data — not needed for inference.
- Speaker diarization (CAM++) — extra model dependency, not needed yet.
- The `runtime/llama.cpp` GGUF/edge build — CPU/edge-only C++ binary, useful
  later for offline/on-device deployment, not needed for a server-side API.
- ONNX export — SenseVoice supports it (`funasr-onnx`) for lower-latency CPU
  inference; add `export_onnx.py` here if p95 latency becomes a problem.

## Licensing

- Upstream source code: MIT. We don't redistribute any of it (see above), so
  no attribution file is needed here — we depend on their `funasr` package
  the normal way, via `pip install`.
- Model weights (`iic/SenseVoiceSmall`): separate license, see the
  [model card](https://huggingface.co/FunAudioLLM/SenseVoiceSmall) and
  [FunASR Model License](https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE).
  Commercial use is permitted per the maintainers' clarification linked in
  the upstream README; re-check before any fine-tuning/redistribution of
  derivative weights.

## Data retention / PII — unresolved, see RETENTION_OPTIONS.md

No decision has been made on whether/how transcripts or audio get retained.
Given this product serves survivors of domestic and sexual violence, that is
explicitly **not** an engineering call to make solo — see
`RETENTION_OPTIONS.md` for the options and tradeoffs. Do not point this
service at real user audio until that's resolved.

## Authentication

`POST /v1/transcribe` requires `Authorization: Bearer <token>`, checked
against the `SPEECH_SERVICE_TOKEN` env var, constant-time compared. **Fails
closed**: if `SPEECH_SERVICE_TOKEN` isn't set, every request is rejected
with `503` rather than the service running open. `GET /health` is
unauthenticated, for liveness checks. (This mirrors `lea-ai`'s own
`SERVICE_TOKEN` convention described in `CLAUDE.md` — independently arrived
at the same pattern, not copied from it.)

This is a shared-secret bearer token, not a full auth system (no per-caller
identity, no expiry, no rotation) — fine for a service reached only by
trusted internal callers, not for anything beyond that.

## Run locally

```bash
export SPEECH_SERVICE_TOKEN=dev-token-change-me   # required — service fails closed without it
pip install -r requirements.txt
python app.py           # http://localhost:50000
```

## Run with Docker

```bash
docker build -t lea-speech .
docker run -e SPEECH_SERVICE_TOKEN=dev-token-change-me -p 50000:50000 lea-speech          # CPU
docker run -e SPEECH_SERVICE_TOKEN=... -e SENSEVOICE_DEVICE=cuda:0 --gpus all -p 50000:50000 lea-speech
```

Cold start downloads ~1GB of model weights into the container on first run
and can take several minutes (confirmed via a real `docker build` + `docker
run` smoke test) — mount a persistent volume at `/root/.cache/modelscope`
in any real deployment, or the model re-downloads on every container
restart. A readiness/liveness probe against `/health` should allow a
generous startup grace period for this reason.

No hosting decision has been made — this needs a real container host
(Cloud Run, Fly.io, ECS, etc.), which is itself a decision this proposal
doesn't make.

## API

`POST /v1/transcribe` — multipart form, field `file` (wav/mp3, any length). Requires auth, see above.

```bash
curl -H "Authorization: Bearer $SPEECH_SERVICE_TOKEN" -F "file=@call.wav" http://localhost:50000/v1/transcribe
```

```json
{
  "text": "😊I'm doing okay today.",
  "clean_text": "I'm doing okay today.",
  "language": "en",
  "emotion": "NEUTRAL",
  "events": ["Speech"],
  "segments": [
    {"start_ms": 0, "end_ms": 2400, "text": "...", "clean_text": "...", "language": "en", "emotion": "NEUTRAL", "events": ["Speech"]}
  ]
}
```

Audio decoding uses `soundfile`, not `torchaudio.load()` — the installed
`torchaudio` routes `.load()` through `torchcodec`, which in turn needs a
system FFmpeg install; `soundfile` (libsndfile) avoids that extra system
dependency for WAV/FLAC/OGG input.

## Testing

```bash
pip install -r requirements-dev.txt
pytest tests/
```

Minimal pytest suite (`tests/test_service.py`), scoped to this service only —
uses FastAPI's `TestClient`, no separate server process needed. Covers auth
(missing/wrong token), validation (wrong file type, undecodable audio,
oversized file), and real wav/mp3 transcription — including a synthesized
trigger-phrase clip (`tests/fixtures/trigger_weapon.wav`, see
`tests/fixtures/README.md` for how it was generated) verified to transcribe
correctly. It does **not** assert anything about `src/guardrails/` — this
service doesn't call into it; that integration is an open question for the
guardrails owners, not something this PR decides.

## Open questions for the team (not resolved by this PR)

- Where does this actually get hosted? (Not Workers — see above.)
- Should `src/guardrails/classifier.py` consume `emotion`/`events` at all,
  and if so, how? This proposal doesn't touch `classifier.py`.
- Does this overlap or conflict with `lea-be-core`'s existing `voice_chat`
  (Gemini Live) feature, or is it a genuinely separate use case (batch
  upload vs. live conversation)? Written as the latter here, worth
  confirming with whoever owns `voice_chat`.
- Retention/PII policy (see `RETENTION_OPTIONS.md`).
