# ── Stage 1: build the React frontend ─────────────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python API that also serves the built frontend ──────────────────
FROM python:3.12-slim

# Set to "true" to bake the local Whisper/BART/Flan-T5 stack into the image
# (needed only when running without an API key; image grows to ~3 GB).
ARG INSTALL_LOCAL_MODELS=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/app/data \
    FRONTEND_DIST=/app/frontend/dist \
    HF_HOME=/app/.cache/huggingface \
    XDG_CACHE_HOME=/app/.cache \
    PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (uid 1000 is also what Hugging Face Spaces expects)
RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY requirements.txt requirements-local.txt ./
RUN pip install -r requirements.txt \
    && if [ "$INSTALL_LOCAL_MODELS" = "true" ]; then \
         pip install torch --index-url https://download.pytorch.org/whl/cpu \
         && pip install -r requirements-local.txt; \
       fi

COPY backend/ ./backend/
COPY --from=frontend /build/dist ./frontend/dist
RUN mkdir -p /app/data /app/.cache && chown -R app:app /app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health', timeout=4)" || exit 1

# --proxy-headers so rate limiting sees real client IPs behind the host's load balancer
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
