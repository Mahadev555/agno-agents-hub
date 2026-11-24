from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.routes import router
from connection import init_db
from config import get_settings
from logging_config import configure_logging
from services.run_service import RunService
import logging
from contextlib import asynccontextmanager

# Settings are validated once at import; a bad value fails here rather than at
# the moment it is first needed.
settings = get_settings()
ALLOWED_ORIGINS = settings.cors_origins
ALLOW_CREDENTIALS = settings.allow_credentials

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log = logging.getLogger("agno_hub")

    log.info(f"Starting agno_hub Hub API (env={settings.environment})...")
    # Fail fast in production rather than issuing tokens signed with an
    # ephemeral key that changes on every deploy.
    settings.resolved_jwt_secret()
    try:
        init_db()
        # Runs execute in-process, so anything left mid-flight by a previous
        # process can never finish. Close them out rather than leaving them
        # stuck in `running` forever.
        RunService.reap_orphans()
        log.info("API ready for requests")
    except Exception as e:
        log.warning(f"Database initialization failed: {e}")
        log.warning("The API will run, but database operations may fail")
    yield
    # Shutdown: anything that needs to happen before the app stops
    print("=" * 60)
    print("Shutting down agno_hub Hub API...")

app = FastAPI(
    title="agno_hub Hub API",
    description="Agent management and talent acquisition system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Liveness probe that does not touch the database."""
    return {"status": "ok"}

# Include API routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=5000, reload=True)
