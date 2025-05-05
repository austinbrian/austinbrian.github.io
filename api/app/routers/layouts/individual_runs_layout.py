from datetime import date

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
                    ],
                    style={
                        "display": "flex",
                        "justify-content": "space-between",
                        "margin-left": "20px",
                        "margin-right": "20px",
                    },
                ),
                html.Div(
                    id="weekly-runs-container",
                    children=[],
                    style={"margin-top": "20px"},
                ),
            ],
        ),
    ],
    style={
        "margin-bottom": "10px",
        "margin-top": "10px",
        "margin-left": "10px",
        "margin-right": "10px",
    },
)
