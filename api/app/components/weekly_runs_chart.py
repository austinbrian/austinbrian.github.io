import logging

import pandas as pd
import plotly.graph_objects as go
from dash import dcc

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def create_weekly_runs_chart(week_start, week_data):
    """Create a chart showing runs for a single week."""

    # Create a figure for the week
    fig = go.Figure()

    # Initialize arrays for the entire week
    x_values = list(range(7))  # Days 0-6
    y_values = [0] * 7  # All points on same y-level
    sizes = [0] * 7  # Initialize sizes
    hover_texts = [""] * 7  # Initialize hover texts

    # Group runs by day of week
    for day in range(7):
        day_date = week_start + pd.Timedelta(days=day)
        day_data = week_data[week_data["normalized_start_date"] == day_date]

        if not day_data.empty:
            # Sum up total distance for the day
            total_distance = day_data["distance"].sum()
            sizes[day] = total_distance**1.15

            # Create hover text for all runs that day
            runs_text = "<br>".join(
                [
                    f"Run: {run['name']}<br>"
                    f"Distance: {run['distance']:.2f} miles<br>"
                    f"Time: {run['moving_time'] / 60:.1f} min<br>"
                    f"Pace: {run['moving_time'] / run['distance'] / 60:.1f} min/mile<br>"
                    f"Elevation: {run['total_elevation_gain']:.0f} ft<br>"
                    f"Start: {run['start_date'].strftime('%Y-%m-%d %I:%M %p')}"
                    for _, run in day_data.iterrows()
                ]
            )
            hover_texts[day] = (
                f"Day Total: {total_distance:.2f} miles<br><br>{runs_text}"
            )
        else:
            hover_texts[day] = "No runs"

    # Add a single scatter plot for the entire week
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="markers",
            marker=dict(
                size=sizes,
                sizemode="area",
                sizeref=2.0 * max(sizes) / (30.0**2)
                if max(sizes) > 0
                else 1,  # Increased size variation
                sizemin=4,
                color="#E67E22",  # Burnt orange color
                opacity=0.7,
            ),
            text=hover_texts,
            hoverinfo="text",
            name="Daily Distance",
        )
    )

    # Update layout
    fig.update_layout(
        title=f"Week of {week_start.date()}",
        xaxis=dict(
            ticktext=[
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
            tickvals=list(range(7)),
            range=[-0.5, 6.5],
            showgrid=False,
            gridcolor="lightgray",
            showline=False,  # Remove vertical lines
        ),
        yaxis=dict(
            showticklabels=False,
            range=[-1, 1],
            showgrid=False,
            zeroline=False,
            showline=False,
        ),
        showlegend=False,
        height=150,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="white",
    )

    return dcc.Graph(figure=fig)
