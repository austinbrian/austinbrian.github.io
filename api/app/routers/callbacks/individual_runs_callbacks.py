import logging

import pandas as pd
from app.components.weekly_runs_chart import create_weekly_runs_chart
from dash import Input, Output, callback

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@callback(
    Output("individual-runs-data-store", "data"),
    Input("individual-runs-date-range-picker", "start_date"),
    Input("individual-runs-date-range-picker", "end_date"),
    Input("refresh-button", "n_clicks"),
)
def update_individual_runs_data_store(start_date, end_date, n_clicks):
    # This will be implemented in the running.py router
    from asyncio import run

    from app.routers import running

    data = run(
        running.get_individual_runs_data(start_date=start_date, end_date=end_date)
    )
    logger.info(f"Loading data for {start_date} to {end_date}: {len(data)} records")
    return data


@callback(
    Output("weekly-runs-container", "children"),
    Input("individual-runs-data-store", "data"),
)
def update_weekly_runs_charts(data):
    if not data:
        return []

    df = pd.DataFrame.from_records(data)

    # Convert start_date to datetime and create normalized version for grouping
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["normalized_start_date"] = df["start_date"].dt.normalize()

    # Group by week (Monday to Sunday)
    df["week_start"] = df["normalized_start_date"] - pd.to_timedelta(
        df["normalized_start_date"].dt.dayofweek, unit="D"
    )
    weeks = df.groupby("week_start")

    charts = []
    for week_start, week_data in sorted(weeks, key=lambda x: x[0], reverse=True):
        charts.append(create_weekly_runs_chart(week_start, week_data))

    return charts
