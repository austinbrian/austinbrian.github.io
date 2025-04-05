from pathlib import Path

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

# Mount Jekyll static site
jekyll_site_path = (
    Path(__file__).parent.parent.parent / "frontend" / "jekyll_site" / "_site"
)
app.mount("/", StaticFiles(directory=str(jekyll_site_path), html=True), name="static")

# Strava routes will be imported from a separate module
from .routers import strava

app.include_router(strava.router, prefix="/strava", tags=["strava"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
