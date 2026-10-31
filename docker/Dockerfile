# Multi-arch: builds the same on your Ubuntu laptop (amd64) and the Pi 5 (arm64).
FROM python:3.12-slim AS base

WORKDIR /app

# Server deps only. The CLI client stays dependency-free and is NOT installed in this image.
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine/ ./engine/
COPY storage/ ./storage/
COPY server/ ./server/
COPY web/ ./web/
COPY packs/community/ ./packs/community/

# SQLite file and any uploaded packs live here, mounted as a volume so they survive a rebuild.
VOLUME ["/data"]
ENV ASCEND_HOME=/data

EXPOSE 8420
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8420/api/health')" || exit 1

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8420"]
