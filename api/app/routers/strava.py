import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
from app.db import (
    get_latest_activity_date,
    get_running_activities,
    init_db,
    store_activities,
)
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

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
    store_activities(activities)
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
                        "relative_effort": activity.get("relative_effort", 0),
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
async def get_activities(
    start_date: Optional[str] = None, end_date: Optional[str] = None
):
    """Get recent Strava activities."""
    activities = await get_all_activities_from_strava(
        start_date=start_date, end_date=end_date
    )
    return activities


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/totals")
def get_totals(start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
    """Get totals for running activities."""
    df = get_running_activities(start_date, end_date)
    return len(df)
