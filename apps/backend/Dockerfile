# syntax=docker/dockerfile:1.4
# --- Backend (FastAPI) ---
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app:/apps

WORKDIR /app

# Dependencias base (build + healthcheck). OCR/PDF opcional.
ARG INSTALL_OCR=false
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
  && if [ "$INSTALL_OCR" = "true" ]; then apt-get install -y --no-install-recommends tesseract-ocr poppler-utils; fi \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Use BuildKit cache for pip to avoid re-downloading wheels on rebuilds
# Also re-enable pip cache for this layer to speed up dev builds
RUN --mount=type=cache,target=/root/.cache/pip \
    PIP_NO_CACHE_DIR=0 pip install --prefer-binary -r requirements.txt

COPY . .

# Usuario no-root
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Default command (override in compose if needed)
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","2","--app-dir","/app"]


