# Build the React app, then serve it from the API container so there is one
# artifact to deploy.
FROM node:22-slim AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

# Bytecode caching off and unbuffered output so logs appear in `docker logs`
# immediately rather than when the buffer fills.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# psycopg2 needs libpq at runtime; the -dev headers are only needed to build it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn \
    && apt-get purge -y --auto-remove build-essential

COPY backend/ ./
COPY --from=frontend /frontend/dist ./static

# Run as a non-root user: a container process that does not need root should
# not have it.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:5000/health || exit 1

# One worker by default: the run event bus is in-process, so a client streaming
# /api/runs/{id}/events must reach the worker executing that run. Scaling out
# requires moving the bus to Redis first (see services/run_bus.py).
ENV WEB_CONCURRENCY=1

CMD ["sh", "-c", "alembic upgrade head && gunicorn app:app \
     --worker-class uvicorn.workers.UvicornWorker \
     --workers ${WEB_CONCURRENCY} \
     --bind 0.0.0.0:5000 \
     --timeout 600 \
     --graceful-timeout 30 \
     --access-logfile -"]
