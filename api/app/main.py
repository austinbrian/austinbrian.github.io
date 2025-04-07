import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Brian Austin's Website API")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include Strava routes first
from .routers import strava

app.include_router(strava.router, prefix="/strava", tags=["strava"])

# Get Jekyll site path from environment variable
jekyll_site_path = os.getenv("JEKYLL_SITE_PATH", "/app/static")

# Mount the Jekyll static site last, so API routes take precedence
app.mount("/", StaticFiles(directory=jekyll_site_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
