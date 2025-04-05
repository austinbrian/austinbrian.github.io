import os
from datetime import datetime, timedelta
from typing import Dict, List

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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


@router.get("/weekly_running")
async def get_weekly_running():
    """Get weekly running distance for the past year."""
    token = await get_access_token()

    # Get activities for the past year
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "after": int(one_year_ago.timestamp()),
                "per_page": 200,  # Maximum allowed by Strava
            },
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch Strava activities",
            )

        activities = response.json()

    # Filter running activities and create DataFrame
    running_activities = [
        {
            "distance": activity["distance"] * 0.000621371,  # Convert meters to miles
            "start_date": datetime.strptime(
                activity["start_date"], "%Y-%m-%dT%H:%M:%SZ"
            ),
        }
        for activity in activities
        if activity["type"] == "Run"
    ]

    df = pd.DataFrame(running_activities)

    # Add week number and group by week
    df["week"] = df["start_date"].dt.isocalendar().week
    df["year"] = df["start_date"].dt.isocalendar().year
    weekly_distance = df.groupby(["year", "week"])["distance"].sum().reset_index()

    # Create the bar chart
    fig = go.Figure(
        data=[
            go.Bar(
                x=[
                    f"{row['year']}-W{row['week']}"
                    for _, row in weekly_distance.iterrows()
                ],
                y=weekly_distance["distance"],
                text=weekly_distance["distance"].round(1),
                textposition="auto",
            )
        ]
    )

    fig.update_layout(
        title="Weekly Running Distance (Miles)",
        xaxis_title="Week",
        yaxis_title="Distance (miles)",
        template="plotly_dark",
        showlegend=False,
        xaxis=dict(tickangle=45),
    )

    return fig.to_json()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
