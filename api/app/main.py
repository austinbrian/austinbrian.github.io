import os

from app.routers import running, strava

# Import and include Dash routes
from app.routers.dashapp import app as dashapp_app
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.staticfiles import StaticFiles

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Brian Austin's Website API",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Mount the Dash app with WSGIMiddleware
app.mount("/app", WSGIMiddleware(dashapp_app.server))

# Import and include Strava routes first
app.include_router(strava.router, prefix="/strava", tags=["strava"])
app.include_router(running.router, prefix="/running", tags=["running"])

# Get Jekyll site path from environment variable or use default
# In Railway, the path will be relative to the project root
jekyll_site_path = os.getenv("JEKYLL_SITE_PATH", "frontend/jekyll_site/_site")

# Mount the Jekyll static site last, so API routes take precedence
app.mount("/", StaticFiles(directory=jekyll_site_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
