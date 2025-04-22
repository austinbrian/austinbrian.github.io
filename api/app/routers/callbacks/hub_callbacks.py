import logging

from app.db import get_running_activities
from app.routers import strava
from dash import Input, Output, callback, html

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# This demonstrates how to use a callback either from the db or from the router


@callback(
    Output("running-data-totals", "children"),
    Input("running-data-totals", "children"),
)
def update_running_data_totals(n_clicks):
    df = get_running_activities()

    return html.Div(
        html.P(f"Total activities this year: {df.shape[0]}"),
    )


@callback(
    Output("running-data-strava-endpoint", "children"),
    Input("running-data-strava-endpoint", "children"),
)
def update_running_data_strava_endpoint(n_clicks):
    logger.info("Updating Strava endpoint")
    num = strava.get_totals()
    return html.Div(
        html.P(f"Total activities this year: {num}"),
        style={"visibility": "hidden"},
    )
