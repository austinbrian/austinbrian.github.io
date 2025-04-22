import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

dash.register_page(
    __name__,
    path="/",
    title="Home",
    description="Home page",
    redirect_from=["/"],
)


right_jumbotron = dbc.Col(
    html.Div(
        id="api-div",
        children=[
            html.H2("API Docs", className="display-3"),
            html.Hr(className="my-2"),
            html.P("See documentation for the API and learn how to use it."),
            dcc.Link(
                dbc.Button(
                    id="api-frontpage-button",
                    children="Go to API",
                    color="light",
                    outline=True,
                    size="lg",
                    n_clicks=0,
                ),
                href="/docs",
                refresh=True,
            ),
        ],
        className="h-100 p-5 text-white bg-info rounded-3",
    ),
    md=6,
)

left_jumbotron = dbc.Col(
    html.Div(
        id="app-div",
        children=[
            html.H2("Running Data", className="display-3"),
            html.Hr(className="my-2"),
            html.P("Visualize running data from Strava."),
            dcc.Link(
                dbc.Button(
                    id="app-frontpage-button",
                    children="Go to Running Hub",
                    color="secondary",
                    outline=True,
                    size="lg",
                ),
                href="/app/hub/",
                refresh=True,
            ),
        ],
        className="h-100 p-5 bg-light border rounded-3",
    ),
    md=6,
)

jumbotron = html.Div(
    [
        dcc.Location(id="frontpage", refresh=True),
        dbc.Row(
            [left_jumbotron, right_jumbotron],
            className="align-items-md-stretch",
            style=dict(margin="0px", padding="10px 10px 10px 10px"),
        ),
    ],
    style=dict(
        height="100%", display="flex", alignItems="center", justifyContent="center"
    ),
)

layout = [
    jumbotron,
]
