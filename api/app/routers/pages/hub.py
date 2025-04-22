import dash
from dash import html

dash.register_page(
    __name__,
    path="/hub/",
    title="Hub",
    description="Main hub page",
    redirect_from=["/hub"],
)

layout = html.Div(
    [
        html.H1("Hub Page"),
        html.Div(
            [
                html.P("Welcome to the hub page!"),
                html.P("This is a separate page from the main Dash app."),
                html.P(html.A("Back to App Home", href="/app/")),
                html.P(html.A("Back to Strava", href="/strava/")),
                html.P(html.A("Back to Bio", href="/about/")),
            ]
        ),
    ]
)
