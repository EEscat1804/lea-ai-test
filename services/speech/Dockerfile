# Dockerfile for services/speech (SenseVoiceSmall ASR + emotion/event tagging).
#
# Build context should be the repo root, so this can copy services/speech/
# as a self-contained unit. On Render, set:
#   Dockerfile Path: services/speech/Dockerfile
#   Docker Build Context Directory: .   (repo root)
#
# The model itself (iic/SenseVoiceSmall) is downloaded on first request, not
# baked into the image — that keeps the image small but means the very first
# transcription after a cold start will be slow (model download + load).
# Render's paid plans keep the instance warm; the free plan spins down when
# idle, so every wake-up would re-pay that first-request cost. Something to
# be aware of if the demo feels slow after inactivity.

FROM python:3.11-slim

# libsndfile1 is required by the `soundfile` package (used in load_audio).
# ffmpeg is NOT required — app.py deliberately avoids the torchaudio/ffmpeg
# path, see the comment in load_audio().
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/speech/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/speech/app.py ./app.py

# Render sets $PORT and expects the container to listen on it. app.py's
# uvicorn.run() call is hardcoded to port=50000 and doesn't read $PORT, so
# rather than edit app.py's entrypoint block, this Dockerfile runs uvicorn
# directly and binds to whatever Render assigns.
ENV SPEECH_SERVICE_HOST=0.0.0.0
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-50000}"]
