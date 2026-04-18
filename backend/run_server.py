#!/usr/bin/env python3
"""
Run the FastAPI server using uvicorn
"""
import uvicorn
import sys
import os

if __name__ == "__main__":
    # Ensure the backend directory is in the Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Run the server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
