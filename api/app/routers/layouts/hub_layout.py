import dash_bootstrap_components as dbc
from app.routers.layouts import (
    cumulative_total_layout,
    date_range_store_layout,
    individual_runs_layout,
    pace_analysis_layout,
)
from dash import dcc, html

layout = html.Div(
    [
        html.H1("Running Hub"),
        dcc.Store(id="cumulative-data-store", data={}),
        dcc.Store(id="individual-runs-data-store", data={}),
        date_range_store_layout.layout,
        dbc.Tabs(
            [
                dbc.Tab(
                    cumulative_total_layout,
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
        html.A("Back to App Home", href="/running/"),
    ],
    style={
        "margin-bottom": "10px",
        "margin-top": "10px",
        "margin-left": "10px",
        "margin-right": "10px",
    },
)
