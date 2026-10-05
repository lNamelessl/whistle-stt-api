# syntax=docker/dockerfile:1
FROM python:3.12-slim@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NEEDLE_TELEMETRY=0 \
    DO_NOT_TRACK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt warmup.py ./
RUN pip install --no-cache-dir -r requirements.txt

# Bake the engine binary + whistle weights into an image layer. The warm-up
# doubles as a smoke test: if the manylinux engine cannot load and transcribe
# on this platform, the build fails here.
RUN python warmup.py && rm -rf /root/.cache/huggingface

COPY app/ ./app/

# Runtime configuration: zero required input. The two NEEDLE pins route the
# engine to the baked files, and HF_HUB_OFFLINE=1 makes any accidental
# network fetch fail loudly instead of silently calling Hugging Face.
ENV PORT=8000 \
    WHISTLE_DEFAULT_LANGUAGE="" \
    CHUNK_LONG_AUDIO=false \
    MAX_UPLOAD_MB=25 \
    MAX_AUDIO_SECONDS=900 \
    API_KEY="" \
    NEEDLE_WHISTLE_WEIGHTS=/app/models/whistle.cact \
    NEEDLE3_LIB_PATH=/app/models/libneedle.so \
    HF_HUB_OFFLINE=1 \
    HOME=/home/whistle

RUN useradd --create-home --uid 1000 whistle \
    && mkdir -p /app/models /home/whistle \
    && chown -R whistle:whistle /app /home/whistle

USER whistle
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --workers 1"]
