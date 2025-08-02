from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from routes.routes import router
import os
from contextlib import asynccontextmanager

# Create client build directory path
client_build_dir = os.path.join("client", "build")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: anything that needs to happen before the app starts
    print("Starting up agno_hub Hub API...")
    yield
    # Shutdown: anything that needs to happen before the app stops
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
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
