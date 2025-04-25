import logging
from asyncio import run

import pandas as pd
import plotly.graph_objects as go
from app.routers import running, strava
from dash import Input, Output, callback, html

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# This demonstrates how to use a callback either from the db or from the router


@callback(
    Output("running-data-totals", "children"),
    Input("cumulative-data-store", "data"),
)
def update_running_data_totals(data):
    df = pd.DataFrame(data)
    total_runs = df.shape[0]
    total_miles = df["distance"].sum()
    return html.Div(
        [
            html.P(f"Total runs: {total_runs}"),
            html.P(f"Total miles: {round(total_miles, 1)}"),
        ],
        style={"display": "flex", "flex-direction": "row", "gap": "10px"},
    )


@callback(
    [
        Output("info-box-1", "children"),
        Output("info-box-2", "children"),
        Output("info-box-3", "children"),
    ],
    Input("cumulative-data-store", "data"),
    Input("cumulative-total-target-slider", "value"),
    Input("cumulative-total-date-range-picker", "start_date"),
    Input("cumulative-total-date-range-picker", "end_date"),
)
def update_info_boxes(data, target, start_date, end_date):
    df = pd.DataFrame(data)
    total_runs = df.shape[0]
    total_miles = df["distance"].sum()
    total_days_run = len(df)

    max_day_run = df["start_date"].max()
    end_date = pd.to_datetime(end_date)
    max_day_run_date = pd.to_datetime(max_day_run)
    max_day_run_miles = df.loc[df.start_date == max_day_run, "distance"].sum()
    max_day_run_miles_rounded = round(max_day_run_miles, 1)
    avg_miles_run = total_miles / total_days_run
    miles_remaining = target - total_miles
    days_remaining = end_date.dayofyear - max_day_run_date.dayofyear
    miles_per_day_remaining = miles_remaining / days_remaining
    print(miles_per_day_remaining)
    miles_per_week_remaining = miles_per_day_remaining * 7
    on_pace_miles = (target * total_days_run) / total_runs

    div1 = html.Div(
        [
            html.H4("Totals"),
            html.P(f"{total_runs} runs"),
            html.P(f"{round(total_miles, 1)} miles"),
        ],
        style={
            "display": "flex",
            "flex-direction": "column",
            "gap": "10px",
            "align-items": "center",
            "justify-content": "center",
        },
    )

    div2 = html.Div(
        [
            html.H4("Max"),
            html.P(f"Longest run: {round(max_day_run_miles, 2)}"),
            html.P(f"Last run: {max_day_run_date.date().strftime('%Y-%m-%d')}"),
        ],
        style={
            "display": "flex",
            "flex-direction": "column",
            "gap": "10px",
            "align-items": "center",
            "justify-content": "center",
        },
    )
    div3 = html.Div(
        [
            html.H4("Progress to Target"),
            html.P(f"{round(avg_miles_run, 2)} avg miles per run"),
            html.P(f"{round(miles_per_week_remaining, 2)} miles per week remaining"),
        ],
        style={
            "display": "flex",
            "flex-direction": "column",
            "gap": "10px",
            "align-items": "center",
            "justify-content": "center",
        },
    )

    return div1, div2, div3


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


@callback(
    Output("cumulative-data-store", "data"),
    Input("cumulative-total-date-range-picker", "start_date"),
    Input("cumulative-total-date-range-picker", "end_date"),
    Input("refresh-button", "n_clicks"),
)
def update_cumulative_data_store(start_date, end_date, n_clicks):
    data = run(
        running.get_cumulative_mileage_data(start_date=start_date, end_date=end_date)
    )
    return data
