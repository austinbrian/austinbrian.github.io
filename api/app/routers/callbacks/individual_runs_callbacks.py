import logging

import dash
import pandas as pd
from app.routers.components.weekly_runs_chart import create_weekly_runs_chart
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate

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


@callback(
    Output("strava-activity-url", "href"),
    Output("strava-activity-url", "target"),
    Input({"type": "weekly-runs-chart", "week": dash.ALL}, "clickData"),
    prevent_initial_call=True,
)
def handle_chart_click(click_data):
    if not click_data or not any(click_data):
        raise PreventUpdate

    # Find the first non-None click data
    for data in click_data:
        if data:
            logger.info(f"Click data: {data}")
            point_index = data["points"][0]["pointIndex"]
            customdata = data["points"][0]["customdata"]
            if customdata and point_index:
                logger.info(f"Customdata: {customdata}")
                logger.info(f"Point index: {point_index}")
                # Get the first activity ID for this day
                activity_id = customdata[0]
                logger.info(f"Opening activity: {activity_id}")
                return f"https://www.strava.com/activities/{activity_id}", "_blank"
            else:
                logger.info(f"No customdata or point_index: {data}")
                raise PreventUpdate

    raise PreventUpdate
