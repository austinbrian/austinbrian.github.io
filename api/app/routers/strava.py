import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.db import (
    get_latest_activity_date,
    get_running_activities_older_than,
    get_running_activities_this_year,
    init_db,
    store_activities,
)
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, Response

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

router = APIRouter()

# Initialize database
init_db()

# Strava API configuration
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

# Validate environment variables
if not all([STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN]):
    raise ValueError(
        "Missing required Strava environment variables. Please check your .env file."
    )


@router.get("/sync")
async def sync_activities():
    """Sync new activities from Strava API."""
    try:
        # Get the latest activity date from the database
        latest_date = get_latest_activity_date()

        if latest_date:
            # Convert to Unix timestamp for Strava API
            after_timestamp = int(latest_date.timestamp())
            logger.info(f"Fetching activities after {latest_date}")
        else:
            # If no activities in database, fetch last 30 days
            after_timestamp = int((datetime.now() - timedelta(days=30)).timestamp())
            logger.info("No activities in database, fetching last 30 days")

        # Fetch new activities from API
        activities = await get_all_activities(after=after_timestamp)

        if not activities:
            return {"message": "No new activities found", "count": 0}

        # Store new activities in database
        store_activities(activities)

        return {
            "message": "Successfully synced activities",
            "count": len(activities),
            "latest_date": max(activity["start_date"] for activity in activities),
        }
    except Exception as e:
        logger.error(f"Error syncing activities: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error syncing activities: {str(e)}"
        )


async def get_access_token() -> str:
    """Get a fresh access token using the refresh token."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.strava.com/oauth/token",
                json={
                    "client_id": STRAVA_CLIENT_ID,
                    "client_secret": STRAVA_CLIENT_SECRET,
                    "refresh_token": STRAVA_REFRESH_TOKEN,
                    "grant_type": "refresh_token",
                    "scope": "activity:read_all",
                },
            )
            if response.status_code != 200:
                logger.error(
                    f"Failed to get access token. Status: {response.status_code}, Response: {response.text}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to get access token",
                )
            return response.json()["access_token"]
    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting access token: {str(e)}"
        )


async def get_all_activities(
    after: Optional[int] = None, per_page: int = 200
) -> List[Dict]:
    """Get Strava activities with pagination support."""
    try:
        token = await get_access_token()
        all_activities = []
        page = 1

        while True:
            async with httpx.AsyncClient() as client:
                params = {"per_page": per_page, "page": page}
                if after:
                    params["after"] = after

                response = await client.get(
                    "https://www.strava.com/api/v3/athlete/activities",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch activities. Status: {response.status_code}, Response: {response.text}"
                    )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to fetch activities",
                    )

                activities = response.json()
                if not activities:  # No more activities to fetch
                    break

                all_activities.extend(activities)
                page += 1

                # If we got fewer activities than requested, we've reached the end
                if len(activities) < per_page:
                    break

        logger.info(f"Retrieved {len(all_activities)} total activities")

        # Store activities in database
        store_activities(all_activities)

        return all_activities
    except Exception as e:
        logger.error(f"Error fetching activities: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching activities: {str(e)}"
        )


@router.get("/activities")
async def get_activities():
    """Get recent Strava activities."""
    try:
        # First try to get from database
        df = get_running_activities_older_than(7)  # Get last 7 days
        if not df.empty:
            return df.to_dict("records")

        # If no data in database, fetch from API
        token = await get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.strava.com/api/v3/athlete/activities",
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code != 200:
                logger.error(
                    f"Failed to fetch activities. Status: {response.status_code}, Response: {response.text}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch activities",
                )
            activities = response.json()
            store_activities(activities)
            return activities
    except Exception as e:
        logger.error(f"Error fetching activities: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching activities: {str(e)}"
        )


@router.get("/stats")
async def get_stats():
    """Get aggregated statistics and generate visualizations."""
    # First try to get from database
    df = get_all_activities()
    if df.empty:
        # If no data in database, fetch from API
        activities = await get_all_activities()
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
    try:
        # First try to get from database
        df = get_running_activities_older_than(365)
        if df.empty:
            # If no data in database, fetch from API
            now = datetime.now()
            one_year_ago = now - timedelta(days=365)
            activities = await get_all_activities(after=int(one_year_ago.timestamp()))
            running_activities = [
                {
                    "distance": activity["distance"]
                    * 0.000621371,  # Convert meters to miles
                    "start_date": datetime.strptime(
                        activity["start_date"], "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
                for activity in activities
                if activity["type"] == "Run"
            ]
            df = pd.DataFrame(running_activities)
        else:
            # Convert distance from meters to miles
            df["distance"] = df["distance"] * 0.000621371
            df["start_date"] = pd.to_datetime(df["start_date"])
            running_activities = df[["distance", "start_date"]].to_dict("records")

        if not running_activities:
            logger.warning("No running activities found")
            return Response(
                content="<div>No running activities found</div>", media_type="text/html"
            )

        # Add week number and group by week
        df["week"] = df["start_date"].dt.isocalendar().week
        df["year"] = df["start_date"].dt.isocalendar().year
        weekly_distance = df.groupby(["year", "week"])["distance"].sum().reset_index()

        logger.info(f"Created weekly distance data with {len(weekly_distance)} weeks")

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

        # Generate HTML with Plotly.js included
        html = fig.to_html(full_html=True, include_plotlyjs=True)
        return Response(content=html, media_type="text/html")
    except Exception as e:
        logger.error(f"Error generating weekly running chart: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error generating weekly running chart: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/cumulative_mileage")
async def get_cumulative_mileage(
    target: Optional[int] = Query(2000, description="Target annual mileage"),
):
    """Get cumulative running distance for the current year with target pace line."""
    try:
        # First try to get from database
        df = get_running_activities_this_year()
        if df.empty:
            # If no data in database, fetch from API
            now = datetime.now()
            start_of_year = datetime(now.year, 1, 1)
            activities = await get_all_activities(after=int(start_of_year.timestamp()))
            running_activities = [
                {
                    "distance": activity["distance"]
                    * 0.000621371,  # Convert meters to miles
                    "start_date": datetime.strptime(
                        activity["start_date"], "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
                for activity in activities
                if activity["type"] == "Run"
            ]
            df = pd.DataFrame(running_activities)
        else:
            # Convert distance from meters to miles
            df["distance"] = df["distance"] * 0.000621371
            df["start_date"] = pd.to_datetime(df["start_date"])
            running_activities = df[["distance", "start_date"]].to_dict("records")

        if not running_activities:
            logger.warning("No running activities found")
            return Response(
                content="<div>No running activities found</div>", media_type="text/html"
            )

        # Add day of year and calculate cumulative sum
        df["day_of_year"] = df["start_date"].dt.dayofyear
        daily_mileage = df.groupby("day_of_year")["distance"].sum().reset_index()
        daily_mileage["cumulative_miles"] = daily_mileage["distance"].cumsum()

        logger.info(f"Created cumulative mileage data with {len(daily_mileage)} days")

        # Create target pace line
        days_in_year = (
            366
            if (now.year % 4 == 0 and now.year % 100 != 0) or (now.year % 400 == 0)
            else 365
        )
        target_pace = pd.DataFrame(
            {
                "day_of_year": range(1, days_in_year + 1),
                "target_miles": [
                    target * (day / days_in_year) for day in range(1, days_in_year + 1)
                ],
            }
        )

        # Create the figure
        fig = go.Figure()

        # Add actual cumulative mileage
        fig.add_trace(
            go.Scatter(
                x=daily_mileage["day_of_year"],
                y=daily_mileage["cumulative_miles"],
                mode="lines+markers",
                name="Actual Miles",
                line=dict(color="#FC4C02"),  # Strava orange
                marker=dict(size=8),
            )
        )

        # Add target pace line
        fig.add_trace(
            go.Scatter(
                x=target_pace["day_of_year"],
                y=target_pace["target_miles"],
                mode="lines",
                name=f"Target Pace ({target} miles/year)",
                line=dict(color="gray", dash="dash"),
                hoverinfo="skip",
            )
        )

        # Add current day marker
        current_day = now.timetuple().tm_yday
        current_miles = (
            daily_mileage["cumulative_miles"].iloc[-1] if not daily_mileage.empty else 0
        )
        fig.add_trace(
            go.Scatter(
                x=[current_day],
                y=[current_miles],
                mode="markers",
                name="Today",
                marker=dict(size=12, color="red", symbol="star"),
            )
        )

        # Update layout
        fig.update_layout(
            title=f"Cumulative Running Distance {now.year}",
            xaxis_title="Day of Year",
            yaxis_title="Cumulative Miles",
            template="plotly_dark",
            showlegend=True,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            annotations=[
                dict(
                    x=current_day,
                    y=current_miles,
                    text=f"Today: {current_miles:.1f} miles",
                    showarrow=True,
                    arrowhead=1,
                    ax=0,
                    ay=-40,
                )
            ],
        )

        # Generate HTML with Plotly.js included
        html = fig.to_html(full_html=True, include_plotlyjs=True)
        return Response(content=html, media_type="text/html")
    except Exception as e:
        logger.error(f"Error generating cumulative mileage chart: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating cumulative mileage chart: {str(e)}",
        )
