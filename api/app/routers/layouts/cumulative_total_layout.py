from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

layout = html.Div(
    [
        html.H2("Cumulative Distance Data"),
        dcc.Store(id="cumulative-data-store", data={}),
        html.Div(
            [
                html.Div(
                    [
                        dcc.DatePickerRange(
                            id="cumulative-total-date-range-picker",
                            min_date_allowed=date(2010, 1, 1),
                            max_date_allowed=date(date.today().year, 12, 31),
                            initial_visible_month=date(
                                date.today().year, date.today().month, 1
                            ),
                            start_date=date(date.today().year, 1, 1),
                            end_date=date(date.today().year, 12, 31),
                            start_date_placeholder_text="Start Date",
                            end_date_placeholder_text="End Date",
                            display_format="YYYY-MM-DD",
                        ),
                        dbc.Button(
                            "↻",
                            id="refresh-button",
                            color="light",
                            className="ms-2",
                            style={
                                "borderRadius": "50%",
                                "width": "38px",
                                "height": "38px",
                                "fontSize": "20px",
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center"},
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "marginLeft": "10px",
                "marginRight": "10px",
            },
        ),
        html.Hr(),
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
                        "flexDirection": "row",
                        "gap": "10px",
                    },
                ),
            ],
            style={
                "display": "flex",
                "flexDirection": "row",
                "gap": "10px",
                "alignItems": "center",
                "justifyContent": "center",
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
                    marks={n: str(n) for n in range(0, 8000, 1000)},
                ),
                html.Div(id="cumulative-total-chart-info", children=""),
                dcc.Graph(
                    id="cumulative-total-chart",
                ),
            ],
        ),
    ],
    style={
        "marginBottom": "10px",
        "marginTop": "10px",
        "marginLeft": "10px",
        "marginRight": "10px",
    },
)
