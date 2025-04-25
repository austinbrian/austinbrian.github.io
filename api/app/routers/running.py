import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
import pandas as pd
from app.db import (
    get_running_activities,
    get_running_activities_older_than,
    init_db,
    store_activities,
)
from app.routers.strava import get_access_token, get_all_activities_from_strava
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


async def get_all_activities_from_db() -> List[Dict]:
    """Get all activities from the database."""
    return get_running_activities()


@router.get("/activities")
async def get_activities(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> List[Dict]:
    """Get recent Strava activities."""
    try:
        # First try to get from database
        df = get_running_activities(start_date, end_date)
        if not df.empty:
            return process_activities(df.to_dict("records"))

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
            return process_activities(activities)
    except Exception as e:
        logger.error(f"Error fetching activities: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching activities: {str(e)}"
        )


def process_activities(activities: List[Dict]) -> List[Dict]:
    return [
        dict(
            **activity,
            **{
                "distance_miles": activity["distance"]
                * 0.000621371,  # Convert meters to miles
                "moving_time_minutes": activity["moving_time"] / 60,
                "total_elevation_gain_feet": activity["total_elevation_gain"] * 3.28084,
                "average_speed_mph": activity["average_speed"] * 2.23694,
                "max_speed_mph": activity["max_speed"] * 2.23694,
                "minutes_per_mile": (activity["moving_time"] / 60)
                / (activity["distance"] * 0.000621371),
            },
        )
        for activity in activities
    ]


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
        logger.debug(f"Created weekly distance data with {len(weekly_distance)} weeks")
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
        logger.debug(f"Using weekly distance data with {len(weekly_distance)} weeks")

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


def convert_to_day_of_year(date, start=None, end=None):
    if start is None:
        start = datetime(now.year, 1, 1)
    if end is None:
        end = datetime(now.year, 12, 31, 23, 59, 59)

    return (date - start).days + 1


@router.get("/cumulative_mileage")
async def get_cumulative_mileage(
    target: Optional[int] = 2000,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    now = datetime.now()
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
    end = end.replace(hour=23, minute=59, second=59)
    logger.debug(f"Start: {start}, End: {end}")
    days_in_year = (end - start).days + 1
    try:
        data = await get_cumulative_mileage_data(
            start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d")
        )
        df = pd.DataFrame(data)

        # Add day of year and calculate cumulative sum
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

        # Add last day marker
        latest_day = convert_to_day_of_year(end, start, end)
        current_day = convert_to_day_of_year(datetime.now(), start, end)
        logger.debug(f"Latest day: {latest_day}")
        current_miles = (
            float(daily_mileage["cumulative_miles"].iloc[-1])
            if not daily_mileage.empty
            else 0
        )
        data.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": "Latest day",
                "x": [latest_day if latest_day < current_day else current_day],
                "y": [current_miles],
                "marker": {"size": 12, "color": "red", "symbol": "star"},
                "text": [end.strftime("%Y-%m-%d")],
            }
        )

        layout = {
            "title": f"Cumulative Running Distance {end.year}",
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


@router.get("/cumulative_mileage_data")
async def get_cumulative_mileage_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    now = datetime.now()
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
    end = end.replace(hour=23, minute=59, second=59)
    logger.debug(f"Start: {start}, End: {end}")
    days_in_year = (end - start).days + 1
    try:
        # First try to get from database
        df = get_running_activities(start_date=start, end_date=end, verbose=False)
        if df.empty:
            # If no data in database, fetch from API
            logger.info("Fetching data from Strava API")
            activities = await get_all_activities_from_strava(
                start_date=start,
                end_date=end,
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

        # Add day of year and calculate cumulative sum
        df["day_of_year"] = df["start_date"].apply(
            convert_to_day_of_year, start=start, end=end
        )
        return df.to_dict("records")
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
