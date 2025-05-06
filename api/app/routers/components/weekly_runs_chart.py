import logging

import pandas as pd
import plotly.graph_objects as go
import pytz
from dash import dcc, html

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def convert_decimal_minutes_to_minutes_seconds(decimal_minutes):
    minutes = int(decimal_minutes)
    seconds = int((decimal_minutes - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def create_weekly_runs_chart(week_start, week_data, size_by="distance"):
    """Create a chart showing runs for a single week.

    Args:
        week_start: Start date of the week
        week_data: DataFrame containing the week's runs
        size_by: Either "distance" or "elevation" to determine circle sizes
    """

    # Create a figure for the week
    fig = go.Figure()

    # Initialize arrays for the entire week
    x_values = list(range(7))  # Days 0-6
    y_values = [0] * 7  # All points on same y-level
    sizes = [0] * 7  # Initialize sizes
    hover_texts = [""] * 7  # Initialize hover texts
    customdata = [None] * 7  # Initialize customdata for activity IDs

    # Calculate total weekly mileage
    total_weekly_miles = week_data["distance"].sum()
    total_weekly_elevation = week_data["total_elevation_gain"].sum()

    # Group runs by day of week
    for day in range(7):
        day_date = week_start + pd.Timedelta(days=day)
        day_data = week_data[week_data["normalized_start_date"] == day_date]

        if not day_data.empty:
            # Sum up total distance and elevation for the day
            total_distance = day_data["distance"].sum()
            total_elevation = day_data["total_elevation_gain"].sum()

            # Set size based on the selected metric
            sizes[day] = total_elevation if size_by == "elevation" else total_distance

            # Create hover text for all runs that day
            runs_text = []
            for _, run in day_data.iterrows():
                run_text = [
                    f'<a href="https://www.strava.com/activities/{run["id"]}" target="_blank">{run["name"]}</a>',
                    f"Distance: {run['distance']:.2f} miles",
                    f"Time: {convert_decimal_minutes_to_minutes_seconds(run['moving_time'] / 60)} min",
                    f"Pace: {convert_decimal_minutes_to_minutes_seconds(run['moving_time'] / run['distance'] / 60)} min/mile",
                    f"Elevation: {run['total_elevation_gain']:.0f} ft",
                    f"Start: {run['start_date'].to_pydatetime().astimezone(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %I:%M %p')}",
                ]
                runs_text.extend(run_text)

            hover_texts[day] = "<br>".join(runs_text)
            # Store activity IDs for this day
            customdata[day] = day_data["id"].tolist()
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
                sizeref=2.0 * max(sizes) / (30.0**2.5)
                if max(sizes) > 0
                else 1,  # Increased size variation
                sizemin=4,
                color="#E67E22",  # Burnt orange color
                opacity=0.7,
            ),
            text=hover_texts,
            hoverinfo="text",
            name="Daily Distance",
            customdata=customdata,
            hoverlabel=dict(
                bgcolor="white", font_size=12, font_family="Arial, sans-serif"
            ),
        )
    )

    # Update layout
    fig.update_layout(
        title=f"Week of {week_start.date().strftime('%B %d, %Y')}",
        title_font=dict(
            family="Arial, sans-serif",
            size=18,
            color="#333333",
        ),
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
            range=[-0.2, 0.2],  # Adjusted range without the horizontal bar
            showgrid=False,
            zeroline=False,
            showline=False,
        ),
        showlegend=False,
        height=150,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="white",
        hovermode="x",
        hoverdistance=300,
        spikedistance=3000,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial, sans-serif"),
    )

    # Create a container with the chart and the total mileage
    return html.Div(
        [
            html.Div(
                [
                    dcc.Graph(
                        figure=fig,
                        config={
                            "displayModeBar": False,
                        },
                        id={
                            "type": "weekly-runs-chart",
                            "week": week_start.date().isoformat(),
                        },
                        style={
                            "width": "90%",
                            "height": "100%",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                f"{total_weekly_elevation:.0f}"
                                if size_by == "elevation"
                                else f"{total_weekly_miles:.1f}",
                                style={
                                    "fontSize": "24px",
                                    "fontWeight": "bold",
                                    "color": "#000080",  # Dark blue
                                    "textAlign": "center",
                                },
                            ),
                            html.Div(
                                "ft" if size_by == "elevation" else "miles",
                                style={
                                    "fontSize": "16px",
                                    "color": "#000080",  # Dark blue
                                    "textAlign": "center",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "justifyContent": "center",
                            "marginLeft": "10px",
                            "minWidth": "80px",  # Ensure consistent width
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "width": "100%",
                    "height": "100%",
                },
            ),
        ],
    )
