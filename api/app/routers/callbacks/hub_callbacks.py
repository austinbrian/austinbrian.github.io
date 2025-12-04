import logging
from asyncio import run

import dash
import pandas as pd
import plotly.graph_objects as go
from app.routers import running, strava
from app.routers.callbacks.individual_runs_callbacks import (
    convert_decimal_minutes_to_minutes_seconds,
)
from dash import Input, Output, callback, html

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
    if data:
        df = pd.DataFrame(data)
        total_runs = df.shape[0]
        total_miles = df["distance"].sum()
        total_days_run = len(df)
        total_minutes_run = df["moving_time"].sum() / 60
        df["minutes_run"] = df["moving_time"] / 60
        df["pace_in_minutes"] = df["minutes_run"] / df["distance"]
        max_day_run = df["start_date"].max()
        max_day_run_pace = df.loc[df.start_date == max_day_run, "pace_in_minutes"].max()
        longest_run = df["distance"].max()
        longest_run_date = pd.to_datetime(
            df.loc[df.distance == longest_run, "start_date"].max()
        )

        longest_run_pace = df.loc[df.distance == longest_run, "pace_in_minutes"].max()
        fastest_run = df["pace_in_minutes"].min()
        fastest_run_date = pd.to_datetime(
            df.loc[df.pace_in_minutes == fastest_run, "start_date"].max()
        )
        fastest_run_distance = df.loc[df.pace_in_minutes == fastest_run, "distance"].max()
        fastest_run_pace = df.loc[
            df.pace_in_minutes == fastest_run, "pace_in_minutes"
        ].max()
        end_date = pd.to_datetime(end_date)
        start_date = pd.to_datetime(start_date)
        max_day_run_date = pd.to_datetime(max_day_run)
        max_day_run_miles = df.loc[df.start_date == max_day_run, "distance"].sum()
        avg_miles_run = total_miles / total_days_run
        miles_remaining = target - total_miles

        # Calculate days elapsed and remaining based on calendar days, not run days
        days_elapsed = (max_day_run_date - start_date).days + 1
        total_days_in_period = (end_date - start_date).days + 1
        days_remaining = (end_date - max_day_run_date).days

        # Calculate pace metrics based on actual calendar days
        avg_miles_per_calendar_day = total_miles / days_elapsed
        on_pace_miles = avg_miles_per_calendar_day * total_days_in_period
        miles_per_day_remaining = miles_remaining / days_remaining if days_remaining > 0 else 0
        miles_per_week_remaining = miles_per_day_remaining * 7
        avg_pace = total_minutes_run / total_miles

        div1 = html.Div(
            [
                html.H4("Totals"),
                html.P(f"{total_runs} runs"),
                html.P(f"{round(total_miles, 1):,.1f} miles"),
                html.P(
                    f"Average pace: {convert_decimal_minutes_to_minutes_seconds(avg_pace)}"
                ),
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
                html.Div(
                    [
                        html.B("Last run:"),
                        html.Div(
                            [
                                html.P(
                                    f"{max_day_run_date.date().strftime('%Y-%m-%d')}, \n"
                                    f"{round(max_day_run_miles, 2):,.2f} miles, \n"
                                    f"pace: {convert_decimal_minutes_to_minutes_seconds(max_day_run_pace)}"
                                )
                            ]
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.B("Longest run:"),
                        html.Div(
                            [
                                html.P(
                                    f"{longest_run_date.date().strftime('%Y-%m-%d')}, \n"
                                    f"{round(longest_run, 2):,.2f} miles, \n"
                                    f"pace: {convert_decimal_minutes_to_minutes_seconds(longest_run_pace)}"
                                )
                            ]
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.B("Fastest run:"),
                        html.Div(
                            [
                                html.P(
                                    f"{fastest_run_date.date().strftime('%Y-%m-%d')}, \n"
                                    f"{round(fastest_run_distance, 2):,.2f} miles, \n"
                                    f"pace: {convert_decimal_minutes_to_minutes_seconds(fastest_run_pace)}"
                                )
                            ]
                        ),
                    ]
                ),
            ],
            style={
                "display": "flex",
                "flex-direction": "column",
                "gap": "5px",
                "align-items": "center",
                "justify-content": "center",
                "padding": "5px",
            },
        )
        div3 = html.Div(
            [
                html.H4("Progress to Target"),
                html.P(f"{round(avg_miles_run, 2)} avg miles per run"),
                html.P(f"On pace for {round(on_pace_miles, 1):,.1f} miles"),
                html.P(
                    f"{round(miles_per_week_remaining, 2):,.1f} miles per week remaining"
                ),
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
    else:
        return dash.no_update, dash.no_update, dash.no_update


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
