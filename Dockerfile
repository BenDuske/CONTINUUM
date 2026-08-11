FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# App code + data
COPY data/ ./data/
COPY scripts/ ./scripts/

# Port (Cloud Run sets PORT env var)
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "continuum.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
