import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


# Initialize DuckDB connection
def get_db():
    return duckdb.connect("strava_data.db")


def init_db():
    """Initialize the database with required tables."""
    with get_db() as conn:
        # Create activities table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id BIGINT PRIMARY KEY,
                name TEXT,
                type TEXT,
                distance FLOAT,
                moving_time INTEGER,
                elapsed_time INTEGER,
                total_elevation_gain FLOAT,
                start_date TIMESTAMP,
                average_speed FLOAT,
                max_speed FLOAT,
                average_cadence FLOAT,
                average_heartrate FLOAT,
                max_heartrate FLOAT,
                last_updated TIMESTAMP
            )
        """)
        logger.info("Database initialized")


def get_latest_activity_date() -> Optional[datetime]:
    """Get the date of the most recent activity in the database."""
    with get_db() as conn:
        result = conn.execute("""
            SELECT MAX(start_date) as latest_date
            FROM activities
        """).fetchone()

        if result and result[0]:
            return result[0]
        return None


def store_activities(activities: List[Dict]):
    """Store activities in the database."""
    if not activities:
        return

    # Convert to DataFrame
    df = pd.DataFrame(activities)

    # Add last_updated timestamp
    df["last_updated"] = datetime.now()

    # Select and rename columns to match our schema
    columns = {
        "id": "id",
        "name": "name",
        "type": "type",
        "distance": "distance",
        "moving_time": "moving_time",
        "elapsed_time": "elapsed_time",
        "total_elevation_gain": "total_elevation_gain",
        "start_date": "start_date",
        "average_speed": "average_speed",
        "max_speed": "max_speed",
        "average_cadence": "average_cadence",
        "average_heartrate": "average_heartrate",
        "max_heartrate": "max_heartrate",
        "last_updated": "last_updated",
    }

    df = df[list(columns.keys())].rename(columns=columns)

    with get_db() as conn:
        # Upsert the data
        conn.execute("""
            INSERT OR REPLACE INTO activities
            SELECT * FROM df
        """)
        logger.info(f"Stored {len(activities)} activities in database")


def get_activities(
    after: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Get activities from the database, optionally filtered by date."""
    with get_db() as conn:
        query = "SELECT * FROM activities"
        params = []

        if start_date:
            query += " WHERE start_date >= ?"
            params.append(start_date)
        elif after:
            query += " WHERE start_date >= ?"
            params.append(after)

        if end_date:
            query += " AND start_date <= ?"
            params.append(end_date)

        return conn.execute(query, params).df()


def get_activities_older_than(
    days: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Get activities older than specified number of days."""
    cutoff_date = datetime.now() - timedelta(days=days)
    return get_activities(after=cutoff_date, start_date=start_date, end_date=end_date)


def get_all_activities() -> pd.DataFrame:
    """Get all activities from the database."""
    return get_activities()


def get_running_activities(
    after: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Get running activities from the database, optionally filtered by date."""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

    if isinstance(after, str):
        after = datetime.strptime(after, "%Y-%m-%d")

    start_date = datetime.strftime(start_date, "%Y-%m-%d") if start_date else None
    end_date = datetime.strftime(end_date, "%Y-%m-%d") if end_date else None
    after = datetime.strftime(after, "%Y-%m-%d") if after else None
    with get_db() as conn:
        query = "SELECT * FROM activities WHERE type = 'Run'"
        params = []

        if start_date:
            query += " AND start_date >= ?"
            params.append(start_date)
        elif after:
            query += " AND start_date >= ?"
            params.append(after)

        if end_date:
            query += " AND start_date <= ?"
            params.append(end_date)

        query += " ORDER BY start_date DESC"

        if verbose:
            logger.info(f"Query: {query}")
            logger.info(f"Params: {params}")

        return conn.execute(query, params).df()


def get_running_activities_older_than(
    days: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Get running activities older than specified number of days."""
    cutoff_date = datetime.now() - timedelta(days=days)
    return get_running_activities(
        after=cutoff_date, start_date=start_date, end_date=end_date
    )


def get_running_activities_this_year(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Get all running activities from the current year."""
    start_of_year = datetime(datetime.now().year, 1, 1)
    return get_running_activities(
        after=start_of_year, start_date=start_date, end_date=end_date
    )
