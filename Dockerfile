FROM python:3.12-slim

WORKDIR /app

# System deps (gcc for clickhouse-connect C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc && \
    rm -rf /var/lib/apt/lists/*

# Python deps — install first for layer caching
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Verify mcp-clickhouse binary is on PATH
RUN which mcp-clickhouse && mcp-clickhouse --help 2>&1 | head -1 || true

# App code + data
COPY data/ ./data/
COPY scripts/ ./scripts/

# Cloud Run sets PORT env var; default to 8080
ENV PORT=8080
EXPOSE 8080

# Use shell form so $PORT is expanded at runtime
CMD uvicorn continuum.web.app:app --host 0.0.0.0 --port $PORT
