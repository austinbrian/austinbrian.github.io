import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load environment variables
load_dotenv()

app = FastAPI(title="Brian Austin's Website API")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Import and include Strava routes first
from app.routers import strava

app.include_router(strava.router, prefix="/strava", tags=["strava"])

# Get Jekyll site path from environment variable or use default
# In Railway, the path will be relative to the project root
jekyll_site_path = os.getenv("JEKYLL_SITE_PATH", "frontend/jekyll_site/_site")

# Mount the Jekyll static site last, so API routes take precedence
app.mount("/", StaticFiles(directory=jekyll_site_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
