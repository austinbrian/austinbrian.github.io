import logging
from datetime import date

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback
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
    [
        Output("pace-chart-date-range-picker", "start_date"),
        Output("pace-chart-date-range-picker", "end_date"),
    ],
    Input("pace-chart-quick-date-range-dropdown", "value"),
    prevent_initial_call=True,
)
def update_pace_chart_date_picker(quick_range):
    logger.info(f"update_pace_chart_date_picker called with quick_range: {quick_range}")
    if not quick_range:
        logger.info("No quick_range value, raising PreventUpdate")
        raise PreventUpdate

    today = date.today()

    if quick_range == "ytd":
        result = {
            "start_date": date(today.year, 1, 1).isoformat(),
            "end_date": today.isoformat(),
        }
    elif quick_range == "1y":
        result = {
            "start_date": date(today.year - 1, today.month, today.day).isoformat(),
            "end_date": today.isoformat(),
        }
    elif quick_range == "2y":
        result = {
            "start_date": date(today.year - 2, today.month, today.day).isoformat(),
            "end_date": today.isoformat(),
        }
    elif quick_range == "2020":
        result = {
            "start_date": date(2020, 1, 1).isoformat(),
            "end_date": today.isoformat(),
        }
    else:
        logger.info(f"Unknown quick_range value: {quick_range}, raising PreventUpdate")
        raise PreventUpdate

    logger.info(f"Returning dates: {result['start_date']}, {result['end_date']}")
    return result["start_date"], result["end_date"]


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
