FROM python:3.11-slim

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
RUN chown -R appuser:appuser /app

USER appuser
ENV HOME=/home/appuser
ENV SENSEVOICE_DEVICE=cpu
EXPOSE 50000

# start-period accounts for the multi-minute cold-start model download/load
# documented in README.md — the container isn't "unhealthy" while that runs.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5m --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:50000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "50000"]
