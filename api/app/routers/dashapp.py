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
    assets_folder="assets",
    suppress_callback_exceptions=True,
    prevent_initial_callbacks="initial_duplicate",
)

# Define the layout with page container
navbar = dbc.NavbarSimple(
    children=[
        *[
            dbc.NavItem(
                dbc.NavLink(
                    page["name"],
                    href="/app" + page["path"],
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
                    )
                )
            ),
            dbc.NavItem(
                dbc.NavLink(
                    html.A(
                        "Bio",
                        href="/about/",
                    )
                )
            ),
        ],
    ]
)

# Set the app layout
app.layout = html.Div(
    [
        navbar,
        dash.page_container,  # Use page_container instead of direct layouts
    ]
)

# Register the callbacks
from app.routers.callbacks import *  # noqa

if __name__ == "__main__":
    app.run_server(debug=True)
