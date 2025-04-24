import logging
from asyncio import run

import plotly.graph_objects as go
from app.db import get_running_activities
from app.routers import running, strava
from dash import Input, Output, callback, html

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# This demonstrates how to use a callback either from the db or from the router


@callback(
    Output("running-data-totals", "children"),
    Input("cumulative-total-date-range-picker", "start_date"),
    Input("cumulative-total-date-range-picker", "end_date"),
    Input("refresh-button", "n_clicks"),
)
def update_running_data_totals(start_date, end_date, n_clicks):
    df = get_running_activities(start_date=start_date, end_date=end_date)

    return html.Div(
        html.P(f"Total runs in period: {df.shape[0]}"),
    )


@callback(
    Output("running-data-strava-endpoint", "children"),
    Input("running-data-strava-endpoint", "children"),
)
def update_running_data_strava_endpoint(n_clicks):
    num = strava.get_totals()
    return html.Div(
        html.P(f"Total activities this year: {num}"),
        style={"visibility": "hidden"},
    )


@callback(
    Output("cumulative-total-chart", "figure"),
    Input("cumulative-total-date-range-picker", "start_date"),
    Input("cumulative-total-date-range-picker", "end_date"),
    Input("cumulative-total-target-slider", "value"),
)
def update_cumulative_total_chart(start_date, end_date, target):
    try:
        data = run(
            running.get_cumulative_mileage(
                target=target, start_date=start_date, end_date=end_date
            )
        )
        fig = go.Figure(**data)
        return fig
    except Exception as e:
        logger.error(f"Error updating cumulative total chart: {e}")
        return None


@callback(
    Output("refresh-button", "disabled"),
    Input("refresh-button", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_running_data(n_clicks):
    run(strava.sync_activities())
    return True
