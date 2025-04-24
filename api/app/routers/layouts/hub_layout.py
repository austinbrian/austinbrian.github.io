from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

layout = html.Div(
    [
        html.H1("Hub Page"),
        html.Div(
            [
                html.H2("Running Data"),
                html.Hr(),
                html.Div(
                    [
                        dcc.DatePickerRange(
                            id="cumulative-total-date-range-picker",
                            min_date_allowed=date(2010, 1, 1),
                            max_date_allowed=date(date.today().year, 12, 31),
                            initial_visible_month=date(date.today().year, 1, 1),
                            start_date=date(date.today().year, 1, 1),
                            end_date=date(date.today().year, 12, 31),
                            start_date_placeholder_text="Start Date",
                            end_date_placeholder_text="End Date",
                            display_format="YYYY-MM-DD",
                        ),
                        dbc.Button("Refresh", id="refresh-button"),
                    ],
                    style={
                        "display": "flex",
                        "justify-content": "space-between",
                        "margin-left": "20px",
                        "margin-right": "20px",
                    },
                ),
                html.Div(id="running-data-totals", children="Totals"),
                html.Div(
                    [
                        dcc.Slider(
                            id="cumulative-total-target-slider",
                            min=0,
                            max=10000,
                            step=500,
                            value=1000,
                            marks={n: str(n) for n in range(0, 10000, 1000)},
                        ),
                        dcc.Graph(
                            id="cumulative-total-chart",
                        ),
                    ],
                ),
            ],
        ),
        html.A("Back to App Home", href="/app/"),
    ],
    style={
        "margin-bottom": "10px",
        "margin-top": "10px",
        "margin-left": "10px",
        "margin-right": "10px",
    },
)
