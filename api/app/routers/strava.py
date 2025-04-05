import os
from typing import Dict, List

import httpx
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

load_dotenv()

router = APIRouter()

# Strava API configuration
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")


async def get_access_token() -> str:
    """Get a fresh access token using the refresh token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "refresh_token": STRAVA_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=401, detail="Failed to refresh Strava token"
            )
        return response.json()["access_token"]


@router.get("/activities")
async def get_activities(limit: int = 30) -> List[Dict]:
    """Get recent Strava activities."""
    access_token = await get_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"per_page": limit},
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch Strava activities",
            )

        activities = response.json()
        return activities


@router.get("/stats")
async def get_stats():
    """Get aggregated statistics and generate visualizations."""
    activities = await get_activities(limit=100)

    # Convert to DataFrame
    df = pd.DataFrame(activities)

    # Basic statistics
    stats = {
        "total_activities": len(df),
        "total_distance": df["distance"].sum() / 1000,  # Convert to km
        "total_time": df["moving_time"].sum() / 3600,  # Convert to hours
        "average_speed": df["average_speed"].mean(),
    }

    # Create time series plot of activities
    if not df.empty:
        df["start_date"] = pd.to_datetime(df["start_date"])
        fig = px.line(
            df, x="start_date", y="distance", title="Activity Distance Over Time"
        )
        stats["distance_plot"] = fig.to_json()

    return stats


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
