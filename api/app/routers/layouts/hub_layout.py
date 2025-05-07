from datetime import date

import dash_bootstrap_components as dbc
from app.routers.layouts.individual_runs_layout import layout as individual_runs_layout
from app.routers.layouts.pace_analysis_layout import layout as pace_analysis_layout
from dash import dcc, html

layout = html.Div(
    [
        html.H1("Hub Page"),
        dcc.Store(id="cumulative-data-store", data={}),
        dcc.Store(id="individual-runs-data-store", data={}),
        dcc.Store(
            id="date-range-store",
            data={
                "start_date": date(date.today().year, 1, 1).isoformat(),
                "end_date": date(date.today().year, 12, 31).isoformat(),
            },
        ),
        dbc.Tabs(
            [
                dbc.Tab(
                    html.Div(
                        [
                            html.H2("Running Data"),
                            html.Hr(),
                            html.Div(
                                [
                                    dcc.DatePickerRange(
                                        id="cumulative-total-date-range-picker",
                                        min_date_allowed=date(2010, 1, 1),
                                        max_date_allowed=date(
                                            date.today().year, 12, 31
                                        ),
                                        initial_visible_month=date(
                                            date.today().year, 1, 1
                                        ),
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
                            html.Div(
                                id="running-data-totals",
                                children="Totals",
                                style={"visibility": "hidden"},
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        id="info-box-container",
                                        children=[
                                            dbc.Card(
                                                id="info-box-1",
                                                children="",
                                                style={"width": "300px"},
                                            ),
                                            dbc.Card(
                                                id="info-box-2",
                                                children="",
                                                style={"width": "300px"},
                                            ),
                                            dbc.Card(
                                                id="info-box-3",
                                                children="",
                                                style={"width": "300px"},
                                            ),
                                        ],
                                        style={
                                            "display": "flex",
                                            "flex-direction": "row",
                                            "gap": "10px",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "flex-direction": "row",
                                    "gap": "10px",
                                },
                            ),
                            html.Div(
                                [
                                    dcc.Slider(
                                        id="cumulative-total-target-slider",
                                        min=0,
                                        max=8000,
                                        step=500,
                                        value=1000,
                                        marks={
                                            n: str(n) for n in range(0, 10000, 1000)
                                        },
                                    ),
                                    html.Div(
                                        id="cumulative-total-chart-info", children=""
                                    ),
                                    dcc.Graph(
                                        id="cumulative-total-chart",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    label="Cumulative Data",
                ),
                dbc.Tab(
                    individual_runs_layout,
                    label="Individual Runs",
                ),
                dbc.Tab(
                    pace_analysis_layout,
                    label="Pace Chart",
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
