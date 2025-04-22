import logging

import dash
import dash_bootstrap_components as dbc
from dash import html
from flask import Flask

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create Flask server
server = Flask(__name__)

# Create the Dash app
app = dash.Dash(
    __name__,
    server=server,
    requests_pathname_prefix="/app/",
    external_stylesheets=[
        # dbc.themes.BOOTSTRAP,
        dbc.themes.FLATLY,
    ],
    use_pages=True,
    assets_folder="frontend/jekyll_site",
    suppress_callback_exceptions=True,
)

# Define the layout with page container
navbar = dbc.NavbarSimple(
    children=[
        *[
            dbc.NavItem(
                dbc.NavLink(
                    page["name"],
                    href="/app" + page["path"],
                    # style={"textDecoration": "none", "color": "darkgray"},
                )
            )
            for page in dash.page_registry.values()
            if page["name"] in ["Hub", "Home", "Programs", "Tickers"]
        ],
        *[
            dbc.NavItem(
                dbc.NavLink(
                    html.A(
                        "Strava",
                        href="/strava/",
                        # style={"textDecoration": "none", "color": "black"},
                    )
                )
            ),
            dbc.NavItem(
                dbc.NavLink(
                    html.A(
                        "Bio",
                        href="/about/",
                        # style={"textDecoration": "none", "color": "black"},
                    )
                )
            ),
        ],
    ]
)
app.layout = html.Div([navbar, dash.page_container])

if __name__ == "__main__":
    app.run_server(debug=True)
