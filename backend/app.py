from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from routes.routes import router
from connection import init_db
import os
from contextlib import asynccontextmanager

# Resolve relative to this file, not the process working directory, so the SPA
# is found whether the server is started from the repo root or from backend/.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
client_build_dir = os.path.join(BACKEND_DIR, "static")

# Comma-separated list of allowed browser origins.
# "*" is only honoured when credentials are disabled, because the CORS spec
# forbids a wildcard origin on credentialed requests.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    if origin.strip()
]
ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
if "*" in ALLOWED_ORIGINS:
    ALLOW_CREDENTIALS = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: anything that needs to happen before the app starts
    print("=" * 60)
    print("Starting agno_hub Hub API...")
    print("=" * 60)
    print("Initializing database...")
    try:
        init_db()
        print("[OK] API ready for requests")
    except Exception as e:
        print(f"[WARNING] Database initialization warning: {e}")
        print("The API will run, but database operations may fail")
    print("=" * 60)
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

# Check if client build directory exists
if os.path.exists(client_build_dir):
    # Mount the React static files directory directly
    app.mount("/static", StaticFiles(directory=os.path.join(client_build_dir, "static")), name="static")
    
    # Mount other static files at root level
    for item in os.listdir(client_build_dir):
        item_path = os.path.join(client_build_dir, item)
        # Skip directories as we've already mounted the static dir
        if os.path.isfile(item_path) and item != "index.html":
            @app.get(f"/{item}")
            async def serve_static_file(item=item):
                return FileResponse(os.path.join(client_build_dir, item))

    # Root route to serve the React app
    @app.get("/")
    async def serve_spa(request: Request):
        return FileResponse(os.path.join(client_build_dir, "index.html"))

    # Fallback route for client-side routing
    @app.get("/{path:path}")
    async def serve_spa_paths(path: str):
        # Check if the path is an API route
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        
        # For all non-API routes, serve the React app
        return FileResponse(os.path.join(client_build_dir, "index.html"))
else:
    print("WARNING: Client build directory not found. React app will not be served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=5000, reload=True)
