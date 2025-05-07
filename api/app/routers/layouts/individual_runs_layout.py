from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

layout = html.Div(
    [
        html.A(
            html.H2("Weekly Run Breakdown"),
            href="/running/log",
            style={
                "textDecoration": "none",
                "color": "inherit",
            },
            className="hover-border",
        ),
        dcc.Store(id="individual-runs-data-store", data={}),
        html.Div(
            [
                html.Hr(),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        dcc.DatePickerRange(
                                            id="individual-runs-date-range-picker",
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
                                    id="individual-runs-quick-date-range-dropdown",
                                    options=[
                                        {"label": "Year to Date", "value": "ytd"},
                                        {"label": "Last 1 Year", "value": "1y"},
                                        {"label": "Last 2 Years", "value": "2y"},
                                        {"label": "Since 2020", "value": "2020"},
                                    ],
                                    value="ytd",
                                    placeholder="Quick Date Range",
                                    clearable=True,
                                    style={"width": "200px", "marginTop": "10px"},
                                ),
                            ],
                            style={"display": "flex", "flexDirection": "column"},
                        ),
                        dbc.RadioItems(
                            id="size-by-toggle",
                            options=[
                                {"label": "Distance", "value": "distance"},
                                {"label": "Elevation", "value": "elevation"},
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
                    id="weekly-runs-container",
                    children=[],
                    style={"marginTop": "20px"},
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
