from dash import html

layout = html.Div(
    [
        html.H1("Hub Page"),
        html.Div(
            [
                html.H2("Running Data"),
                html.Hr(),
                html.Div(id="running-data-totals", children="Totals"),
                html.Div(id="running-data-strava-endpoint", children="Totals"),
                html.A("Back to App Home", href="/app/"),
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
