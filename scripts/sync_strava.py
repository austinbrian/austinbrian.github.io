"""Sync Strava running activities to Cloudflare R2 as JSON.

Downloads existing activities.json from R2 (if any), fetches new activities
from the Strava API, merges and deduplicates, then uploads back to R2.
"""

import json
import logging
import os
import sys
import tempfile
from datetime import datetime

import boto3
import httpx
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Strava API
STRAVA_CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
STRAVA_REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]

# Cloudflare R2
R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "strava-data")
R2_KEY = "activities.json"

# Unit conversion constants
METERS_TO_MILES = 0.000621371
METERS_TO_FEET = 3.28084

ACTIVITY_FIELDS = [
    "id", "name", "type", "distance", "moving_time", "elapsed_time",
    "total_elevation_gain", "start_date", "average_speed", "max_speed",
    "average_cadence", "average_heartrate", "max_heartrate",
]


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def download_existing(client) -> list[dict]:
    """Download existing activities.json from R2."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            client.download_file(R2_BUCKET_NAME, R2_KEY, f.name)
            with open(f.name) as fh:
                data = json.load(fh)
            logger.info(f"Downloaded {len(data)} existing activities from R2")
            return data
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            logger.info("No existing activities in R2, starting fresh")
            return []
        raise


def upload_activities(client, activities: list[dict]):
    """Upload activities.json to R2."""
    body = json.dumps(activities, default=str)
    client.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=R2_KEY,
        Body=body,
        ContentType="application/json",
    )
    logger.info(f"Uploaded {len(activities)} activities to R2")


def get_access_token() -> str:
    """Get a fresh Strava access token using the refresh token."""
    response = httpx.post(
        "https://www.strava.com/oauth/token",
        json={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": STRAVA_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
    )
    response.raise_for_status()
    data = response.json()
    new_refresh = data.get("refresh_token")
    if new_refresh and new_refresh != STRAVA_REFRESH_TOKEN:
        logger.warning(
            "Strava issued a new refresh token. Update your STRAVA_REFRESH_TOKEN secret."
        )
    return data["access_token"]


def fetch_activities(token: str, after: int | None = None) -> list[dict]:
    """Fetch all activities from Strava API with pagination."""
    all_activities = []
    page = 1
    per_page = 200

    while True:
        params: dict = {"per_page": per_page, "page": page}
        if after:
            params["after"] = after

        response = httpx.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        activities = response.json()

        if not activities:
            break

        for activity in activities:
            processed = {field: activity.get(field, 0) for field in ACTIVITY_FIELDS}
            processed["id"] = activity["id"]
            processed["name"] = activity.get("name", "")
            processed["type"] = activity.get("type", "")
            processed["start_date"] = activity.get("start_date", "")
            all_activities.append(processed)

        page += 1
        if len(activities) < per_page:
            break

    logger.info(f"Fetched {len(all_activities)} activities from Strava")
    return all_activities


def enrich_activity(activity: dict) -> dict:
    """Add pre-computed derived fields to an activity."""
    distance_miles = activity["distance"] * METERS_TO_MILES
    moving_time_minutes = activity["moving_time"] / 60
    elevation_feet = activity["total_elevation_gain"] * METERS_TO_FEET
    pace = moving_time_minutes / distance_miles if distance_miles > 0 else 0

    return {
        **activity,
        "distance_miles": round(distance_miles, 4),
        "moving_time_minutes": round(moving_time_minutes, 2),
        "elevation_feet": round(elevation_feet, 1),
        "pace": round(pace, 2),
    }


def get_latest_timestamp(activities: list[dict]) -> int | None:
    """Get the unix timestamp of the most recent activity."""
    if not activities:
        return None
    dates = []
    for a in activities:
        try:
            dt = datetime.fromisoformat(a["start_date"].replace("Z", "+00:00"))
            dates.append(int(dt.timestamp()))
        except (ValueError, KeyError):
            continue
    return max(dates) if dates else None


def main():
    r2 = get_r2_client()

    # Download existing data
    existing = download_existing(r2)
    existing_ids = {a["id"] for a in existing}

    # Determine incremental fetch point
    after = get_latest_timestamp(existing)
    if after:
        logger.info(f"Fetching activities after timestamp {after}")

    # Fetch from Strava
    token = get_access_token()
    new_activities = fetch_activities(token, after=after)

    # Filter to runs only
    new_runs = [a for a in new_activities if a.get("type") == "Run"]
    logger.info(f"Found {len(new_runs)} new runs out of {len(new_activities)} activities")

    # Merge: new activities override existing ones with same ID
    new_ids = {a["id"] for a in new_runs}
    merged = [a for a in existing if a["id"] not in new_ids]
    merged.extend([enrich_activity(a) for a in new_runs])

    # Also enrich any existing activities that lack derived fields
    for i, a in enumerate(merged):
        if "distance_miles" not in a:
            merged[i] = enrich_activity(a)

    # Sort by start_date descending
    merged.sort(key=lambda a: a.get("start_date", ""), reverse=True)

    logger.info(
        f"Total: {len(merged)} runs "
        f"({len(merged) - len(existing)} new, {len(existing_ids & new_ids)} updated)"
    )

    # Upload
    upload_activities(r2, merged)
    logger.info("Sync complete")


if __name__ == "__main__":
    main()
