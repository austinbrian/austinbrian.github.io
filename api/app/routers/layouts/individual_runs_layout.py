from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

layout = html.Div(
    [
        html.H1("Individual Runs"),
        dcc.Store(id="individual-runs-data-store", data={}),
        html.Div(
            [
                html.H2("Weekly Run Breakdown"),
                html.Hr(),
                html.Div(
                    [
                        dcc.DatePickerRange(
                            id="individual-runs-date-range-picker",
                            min_date_allowed=date(2010, 1, 1),
                            max_date_allowed=date(date.today().year, 12, 31),
                            initial_visible_month=date(date.today().year, 1, 1),
                            start_date=date(date.today().year, 1, 1),
                            end_date=date(date.today().year, 12, 31),
                            start_date_placeholder_text="Start Date",
                            end_date_placeholder_text="End Date",
                            display_format="YYYY-MM-DD",
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
                            style={"marginLeft": "20px"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "marginLeft": "20px",
                        "marginRight": "20px",
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
