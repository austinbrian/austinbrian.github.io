import logging
from datetime import date

import dash
import pandas as pd
import plotly.graph_objects as go
from app.routers.components.weekly_runs_chart import create_weekly_runs_chart
from dash import Input, Output, callback, html
from dash.exceptions import PreventUpdate

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def convert_decimal_minutes_to_minutes_seconds(decimal_minutes):
    if pd.isna(decimal_minutes):
        return ""
    minutes = int(decimal_minutes)
    seconds = int((decimal_minutes - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


@callback(
    Output("date-range-store", "data"),
    Input("individual-runs-date-range-picker", "start_date"),
    Input("individual-runs-date-range-picker", "end_date"),
    prevent_initial_call=True,
)
def update_individual_runs_date_range_store(start_date, end_date):
    if not start_date or not end_date:
        raise PreventUpdate
    return {"start_date": start_date, "end_date": end_date}


@callback(
    Output("date-range-store", "data", allow_duplicate=True),
    Input("pace-chart-date-range-picker", "start_date"),
    Input("pace-chart-date-range-picker", "end_date"),
    prevent_initial_call=True,
)
def update_pace_chart_date_range_store(start_date, end_date):
    if not start_date or not end_date:
        raise PreventUpdate
    return {"start_date": start_date, "end_date": end_date}


@callback(
    Output("date-range-store", "data", allow_duplicate=True),
    Input("cumulative-total-date-range-picker", "start_date"),
    Input("cumulative-total-date-range-picker", "end_date"),
    prevent_initial_call=True,
)
def update_cumulative_total_date_range_store(start_date, end_date):
    if not start_date or not end_date:
        raise PreventUpdate
    return {"start_date": start_date, "end_date": end_date}


@callback(
    [
        Output("individual-runs-date-range-picker", "start_date", allow_duplicate=True),
        Output("individual-runs-date-range-picker", "end_date", allow_duplicate=True),
    ],
    Input("date-range-store", "data"),
    prevent_initial_call=True,
)
def sync_individual_runs_date_picker(date_range):
    if not date_range:
        raise PreventUpdate

    return [
        date_range["start_date"],
        date_range["end_date"],
    ]


@callback(
    [
        Output("pace-chart-date-range-picker", "start_date", allow_duplicate=True),
        Output("pace-chart-date-range-picker", "end_date", allow_duplicate=True),
    ],
    Input("quick-date-range-dropdown", "value"),
    Input("date-range-store", "data"),
    prevent_initial_call="initial_duplicate",
)
def update_pace_chart_date_range(quick_range, date_range):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "quick-date-range-dropdown":
        if not quick_range:
            raise PreventUpdate

        today = date.today()

        if quick_range == "ytd":
            return date(today.year, 1, 1), today
        elif quick_range == "1y":
            return date(today.year - 1, today.month, today.day), today
        elif quick_range == "2y":
            return date(today.year - 2, today.month, today.day), today
        elif quick_range == "2020":
            return date(2020, 1, 1), today
    elif trigger_id == "date-range-store" and date_range:
        return date_range["start_date"], date_range["end_date"]

    raise PreventUpdate


@callback(
    Output("individual-runs-data-store", "data"),
    Input("date-range-store", "data"),
    Input("refresh-button", "n_clicks"),
)
def update_individual_runs_data_store(date_range, n_clicks):
    if not date_range:
        raise PreventUpdate

    # This will be implemented in the running.py router
    from asyncio import run

    from app.routers import running

    data = run(
        running.get_individual_runs_data(
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )
    )
    logger.info(
        f"Loading data for {date_range['start_date']} to {date_range['end_date']}: {len(data)} records"
    )
    return data


@callback(
    Output("weekly-runs-container", "children"),
    Input("individual-runs-data-store", "data"),
    Input("size-by-toggle", "value"),
)
def update_weekly_runs_charts(data, size_by):
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
        week_chart = create_weekly_runs_chart(week_start, week_data, size_by)
        # Wrap each week's chart in a div with an HR below it
        charts.append(
            html.Div(
                [
                    week_chart,
                    html.Hr(style={"margin": "20px 0", "borderColor": "#E5E5E5"}),
                ]
            )
        )

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


@callback(
    Output("pace-chart", "figure"),
    Input("individual-runs-data-store", "data"),
    Input("pace-chart-x-axis-toggle", "value"),
)
def update_pace_chart(data, x_axis_type):
    if not data:
        return go.Figure()

    df = pd.DataFrame.from_records(data).query("distance >=1.0")

    # Calculate pace in minutes per mile
    df["pace"] = df["moving_time"] / 60 / df["distance"]  # Convert to minutes per mile

    # Create hover text
    hover_text = []
    for _, run in df.iterrows():
        hover_text.append(
            f"<b>{run['name']}</b><br>"
            f"Distance: {run['distance']:.2f} miles<br>"
            f"Pace: {convert_decimal_minutes_to_minutes_seconds(run['pace'])} min/mile<br>"
            f"Date: {run['start_date']}<br>"
            f"Elevation: {run['total_elevation_gain']:.0f} ft"
        )

    # Create the figure
    fig = go.Figure()

    # Add scatter plot
    fig.add_trace(
        go.Scatter(
            x=df["distance"] if x_axis_type == "distance" else df["start_date"],
            y=df["pace"],
            mode="markers",
            marker=dict(
                size=df["distance"] * 2,  # Scale size by distance
                sizemode="area",
                sizeref=2.0 * max(df["distance"]) / (30.0**2),
                sizemin=4,
                color="#E67E22",  # Burnt orange color
                opacity=0.7,
            ),
            text=hover_text,
            hoverinfo="text",
            customdata=df["id"],  # Store activity IDs for click handling
        )
    )

    # Update layout
    fig.update_layout(
        title="Pace Analysis",
        xaxis_title="Distance (miles)" if x_axis_type == "distance" else "Date",
        yaxis_title="Pace (minutes/mile)",
        yaxis=dict(
            autorange="reversed",  # Reverse y-axis so faster paces are higher
            gridcolor="lightgray",
        ),
        xaxis=dict(
            gridcolor="lightgray",
        ),
        plot_bgcolor="white",
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial, sans-serif",
        ),
    )

    return fig


@callback(
    Output("pace-chart-distribution", "figure"),
    Input("individual-runs-data-store", "data"),
    Input("pace-chart-x-axis-toggle", "value"),
)
def update_pace_distribution(data, x_axis_type):
    if not data:
        return go.Figure()
    if not x_axis_type:
        return go.Figure()

    df = pd.DataFrame.from_records(data).query("distance >=1.0")
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["normalized_start_date"] = df[
        "start_date"
    ].dt.normalize()  # Normalize timestamps

    if x_axis_type == "distance":
        # Create distance bins in half-mile increments
        max_distance = df["distance"].max()
        bins = [
            i * 0.5 for i in range(int(max_distance * 2) + 2)
        ]  # Half-mile increments
        labels = [f"{bins[i]:.1f}-{bins[i + 1]:.1f}" for i in range(len(bins) - 1)]

        # Count runs in each bin
        df["distance_bin"] = pd.cut(df["distance"], bins=bins, labels=labels)
        counts = df["distance_bin"].value_counts().sort_index()

        # Create bar chart
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=counts.index,
                y=counts.values,
                marker_color="#E67E22",
                opacity=0.7,
                text=None,  # Remove bar labels
                textposition="none",  # Ensure no text is shown
            )
        )

        # Add hover text
        hover_text = []
        for bin_label, count in counts.items():
            runs_in_bin = df[df["distance_bin"] == bin_label]
            avg_pace = (
                runs_in_bin["moving_time"] / 60 / runs_in_bin["distance"]
            ).mean()
            hover_text.append(
                f"<b>{bin_label} miles</b><br>"
                f"Number of runs: {count}<br>"
                f"Average pace: {convert_decimal_minutes_to_minutes_seconds(avg_pace)} min/mile"
            )

        fig.update_traces(
            hovertemplate="%{text}<extra></extra>",
            text=hover_text,
        )

        fig.update_layout(
            title="Run Distance Distribution",
            xaxis_title="Distance Range (miles)",
            yaxis_title="Number of Runs",
            xaxis=dict(
                gridcolor="lightgray",
                tickangle=45,  # Angle the labels for better readability
            ),
            yaxis=dict(
                gridcolor="lightgray",
                tickmode="auto",  # Let Plotly determine optimal tick spacing
            ),
            plot_bgcolor="white",
            hovermode="closest",
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial, sans-serif",
            ),
        )
    else:
        # Group by week and sum distances
        df["week_start"] = df["normalized_start_date"] - pd.to_timedelta(
            df["normalized_start_date"].dt.dayofweek, unit="D"
        )
        weekly_distances = df.groupby("week_start")["distance"].sum().reset_index()
        weekly_distances = weekly_distances.sort_values("week_start")  # Sort by date

        # Create bar chart
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=weekly_distances["week_start"],
                y=weekly_distances["distance"],
                marker_color="#E67E22",
                opacity=0.7,
                # width=0.8,  # Make bars wider
                text=None,  # Remove bar labels
                textposition="none",  # Ensure no text is shown
            )
        )

        # Add hover text
        hover_text = []
        for _, row in weekly_distances.iterrows():
            week_runs = df[df["week_start"] == row["week_start"]]
            avg_pace = (week_runs["moving_time"] / 60 / week_runs["distance"]).mean()
            hover_text.append(
                f"<b>Week of {row['week_start'].strftime('%Y-%m-%d')}</b><br>"
                f"Total distance: {row['distance']:.1f} miles<br>"
                f"Number of runs: {len(week_runs)}<br>"
                f"Average pace: {convert_decimal_minutes_to_minutes_seconds(avg_pace)} min/mile"
            )

        fig.update_traces(
            hovertemplate="%{text}<extra></extra>",
            text=hover_text,
        )

        fig.update_layout(
            title="Weekly Running Distance",
            xaxis_title="Week",
            yaxis_title="Total Distance (miles)",
            xaxis=dict(
                gridcolor="lightgray",
                tickformat="%Y-%m-%d",
                tickangle=45,  # Angle the labels for better readability
            ),
            yaxis=dict(
                gridcolor="lightgray",
                tickmode="auto",  # Let Plotly determine optimal tick spacing
            ),
            plot_bgcolor="white",
            hovermode="closest",
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial, sans-serif",
            ),
        )

    return fig


@callback(
    [
        Output("individual-runs-date-range-picker", "start_date", allow_duplicate=True),
        Output("individual-runs-date-range-picker", "end_date", allow_duplicate=True),
    ],
    Input("quick-date-range-dropdown", "value"),
    Input("date-range-store", "data"),
    prevent_initial_call="initial_duplicate",
)
def update_date_range(quick_range, date_range):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "quick-date-range-dropdown":
        if not quick_range:
            raise PreventUpdate

        today = date.today()

        if quick_range == "ytd":
            return date(today.year, 1, 1), today
        elif quick_range == "1y":
            return date(today.year - 1, today.month, today.day), today
        elif quick_range == "2y":
            return date(today.year - 2, today.month, today.day), today
        elif quick_range == "2020":
            return date(2020, 1, 1), today
    elif trigger_id == "date-range-store" and date_range:
        return date_range["start_date"], date_range["end_date"]

    raise PreventUpdate
