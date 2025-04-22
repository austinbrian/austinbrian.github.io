import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
import pandas as pd
import plotly.express as px
from app.db import (
    get_latest_activity_date,
    get_running_activities,
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


@router.get("/seed")
async def seed_activities():
    """Seed activities from Strava API."""
    activities = await get_all_activities_from_strava()
    return activities


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
        activities = await get_all_activities_from_strava(after=after_timestamp)

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


async def get_all_activities_from_db() -> List[Dict]:
    """Get all activities from the database."""
    return get_running_activities()


async def get_all_activities_from_strava(
    after: Optional[int] = None,
    per_page: int = 200,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
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
                if start_date:
                    params["after"] = start_date
                if end_date:
                    params["before"] = end_date

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

                # Process each activity to ensure all required fields are present
                processed_activities = []
                for activity in activities:
                    processed_activity = {
                        "id": activity.get("id"),
                        "name": activity.get("name"),
                        "type": activity.get("type"),
                        "distance": activity.get("distance", 0),
                        "moving_time": activity.get("moving_time", 0),
                        "elapsed_time": activity.get("elapsed_time", 0),
                        "total_elevation_gain": activity.get("total_elevation_gain", 0),
                        "start_date": activity.get("start_date"),
                        "average_speed": activity.get("average_speed", 0),
                        "max_speed": activity.get("max_speed", 0),
                        "average_cadence": activity.get("average_cadence", 0),
                        "average_heartrate": activity.get("average_heartrate", 0),
                        "max_heartrate": activity.get("max_heartrate", 0),
                        "suffer_score": activity.get("suffer_score", 0),
                    }
                    processed_activities.append(processed_activity)

                all_activities.extend(processed_activities)
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
    df = await get_all_activities_from_strava()
    if df.empty:
        # If no data in database, fetch from API
        activities = await get_all_activities_from_strava()
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


@router.get("/weekly_running_data")
async def get_weekly_running_data(
    start_date: Optional[str] = Query(
        None, description="Start date in YYYY-MM-DD format"
    ),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
):
    """Get weekly running distance for the past year."""

    try:
        # First try to get from database
        df = get_running_activities_older_than(365, start_date, end_date)
        if df.empty:
            # If no data in database, fetch from API
            now = datetime.now()
            one_year_ago = now - timedelta(days=365)
            activities = await get_all_activities_from_strava(
                after=int(one_year_ago.timestamp()),
                start_date=start_date,
                end_date=end_date,
            )
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
        return weekly_distance.to_dict("records")
    except Exception as e:
        logger.error(f"Error generating weekly running data: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error generating weekly running data: {str(e)}"
        )


@router.get("/weekly_running_chart")
async def get_weekly_running_chart(
    start_date: Optional[str] = Query(
        None, description="Start date in YYYY-MM-DD format"
    ),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
):
    try:
        weekly_distance = await get_weekly_running_data(
            start_date=start_date,
            end_date=end_date,
        )
        logger.info(f"Using weekly distance data with {len(weekly_distance)} weeks")

        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(weekly_distance)

        # Create week labels
        df["week_label"] = df.apply(
            lambda x: f"{int(x['year'])}-W{int(x['week']):02d}", axis=1
        )

        # Sort by year and week
        df = df.sort_values(["year", "week"])

        # Create the bar chart data
        data = [
            {
                "type": "bar",
                "x": df["week_label"].tolist(),
                "y": df["distance"].tolist(),
                "text": df["distance"].round(1).tolist(),
                "textposition": "auto",
            }
        ]

        layout = {
            "title": "Weekly Running Distance (Miles)",
            "xaxis": {"title": "Week", "tickangle": 45},
            "yaxis": {"title": "Distance (miles)"},
            "template": "plotly_white",
            "showlegend": False,
        }

        return {"data": data, "layout": layout}
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
    start_date: Optional[str] = Query(
        None, description="Start date in YYYY-MM-DD format"
    ),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
):
    try:
        # First try to get from database
        df = get_running_activities_this_year(start_date, end_date)
        now = datetime.now()
        if df.empty:
            # If no data in database, fetch from API
            start_of_year = datetime(now.year, 1, 1)
            activities = await get_all_activities_from_strava(
                after=int(start_of_year.timestamp()),
                start_date=start_date,
                end_date=end_date,
            )
            running_activities = [
                {
                    "distance": float(
                        activity["distance"] * 0.000621371
                    ),  # Convert meters to miles and ensure float
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
            df["distance"] = df["distance"].astype(float) * 0.000621371
            df["start_date"] = pd.to_datetime(df["start_date"])
            running_activities = df[["distance", "start_date"]].to_dict("records")

        if not running_activities:
            logger.warning("No running activities found")
            return {"data": [], "layout": {}}

        start = (
            datetime.strptime(start_date, "%Y-%m-%d")
            if start_date
            else datetime(now.year, 1, 1)
        )

        # Get end date - either from query param or Dec 31 of start year
        end = (
            datetime.strptime(end_date, "%Y-%m-%d")
            if end_date
            else datetime(now.year, 12, 31)
        )

        # Calculate number of days between start and end
        days_in_year = (end - start).days + 1

        def convert_to_day_of_year(date, start=None, end=None):
            if start is None:
                start = datetime(now.year, 1, 1)
            if end is None:
                end = datetime(now.year, 12, 31)

            return (date - start).days + 1

        # Add day of year and calculate cumulative sum
        df["day_of_year"] = df["start_date"].apply(
            convert_to_day_of_year, start=start, end=end
        )
        day_to_date_mapping = df.set_index("day_of_year")["start_date"].to_dict()
        daily_mileage = df.groupby("day_of_year")["distance"].sum().reset_index()
        daily_mileage["cumulative_miles"] = daily_mileage["distance"].cumsum()

        # Create target pace line

        target_pace = pd.DataFrame(
            {
                "day_of_year": range(1, days_in_year + 1),
                "target_miles": [
                    float(target * (day / days_in_year))
                    for day in range(1, days_in_year + 1)
                ],
            }
        )

        # Create the plot data
        data = [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Actual Miles",
                "x": daily_mileage["day_of_year"].tolist(),
                "y": [float(x) for x in daily_mileage["cumulative_miles"].tolist()],
                "line": {"color": "#FC4C02"},
                "marker": {"size": 8},
                "text": [
                    day_to_date_mapping[day].date()
                    for day in daily_mileage["day_of_year"]
                ],
            },
            {
                "type": "scatter",
                "mode": "lines",
                "name": f"Target Pace ({target} miles/year)",
                "x": target_pace["day_of_year"].tolist(),
                "y": [float(x) for x in target_pace["target_miles"].tolist()],
                "line": {"color": "gray", "dash": "dash"},
            },
        ]

        # Add current day marker
        current_day = convert_to_day_of_year(now, start, end)
        current_miles = (
            float(daily_mileage["cumulative_miles"].iloc[-1])
            if not daily_mileage.empty
            else 0
        )
        data.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": "Today",
                "x": [current_day],
                "y": [current_miles],
                "marker": {"size": 12, "color": "red", "symbol": "star"},
                "text": [now.strftime("%Y-%m-%d")],
            }
        )

        layout = {
            "title": f"Cumulative Running Distance {now.year}",
            "xaxis": {"title": "Day of Year"},
            "yaxis": {"title": "Cumulative Miles"},
            "template": "plotly_white",
            "showlegend": True,
            "legend": {"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
        }

        return {"data": data, "layout": layout}
    except Exception as e:
        logger.error(f"Error generating cumulative mileage chart: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating cumulative mileage chart: {str(e)}",
        )


@router.get("/totals")
def get_totals(start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
    """Get totals for running activities."""
    df = get_running_activities(start_date, end_date)
    return len(df)
