from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

layout = html.Div(
    [
        html.H1("Pace Analysis"),
        dcc.Store(id="individual-runs-data-store", data={}),
        dcc.Store(
            id="date-range-store",
            data={
                "start_date": date(date.today().year, 1, 1).isoformat(),
                "end_date": date(date.today().year, 12, 31).isoformat(),
            },
        ),
        html.Hr(),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.DatePickerRange(
                                    id="pace-chart-date-range-picker",
                                    min_date_allowed=date(2010, 1, 1),
                                    max_date_allowed=date(date.today().year, 12, 31),
                                    initial_visible_month=date(date.today().year, 1, 1),
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
                        dcc.Dropdown(
                            id="quick-date-range-dropdown",
                            options=[
                                {"label": "Year to Date", "value": "ytd"},
                                {"label": "Last 1 Year", "value": "1y"},
                                {"label": "Last 2 Years", "value": "2y"},
                                {"label": "Since 2020", "value": "2020"},
                            ],
                            value=None,
                            placeholder="Quick Date Range",
                            clearable=True,
                            style={"width": "200px"},
                        ),
                    ],
                    style={"display": "flex", "flexDirection": "column", "gap": "10px"},
                ),
                dbc.RadioItems(
                    id="pace-chart-x-axis-toggle",
                    options=[
                        {"label": "Distance", "value": "distance"},
                        {"label": "Date", "value": "date"},
                    ],
                    value="distance",
                    inline=True,
                    className="btn-group",
                    inputClassName="btn-check",
                    labelClassName="btn btn-outline-primary",
                    labelCheckedClassName="active",
                    style={"marginLeft": "10px"},
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
        html.Div(
            [
                dcc.Graph(
                    id="pace-chart",
                    style={"height": "600px"},
                ),
                dcc.Graph(
                    id="pace-chart-distribution",
                    style={"height": "600px"},
                ),
            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "20px",
            },
        ),
    ],
    style={
        "marginBottom": "10px",
        "marginTop": "10px",
        "marginLeft": "10px",
        "marginRight": "10px",
    },
)
