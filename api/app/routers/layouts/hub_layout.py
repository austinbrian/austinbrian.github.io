from dash import html

layout = html.Div(
    [
        html.H1("Hub Page"),
        html.Div(
            [
                html.P("Welcome to the hub page!"),
                html.P("This is a separate page from the main Dash app."),
                html.A("Back to Dash", href="/app/"),
            ]
        ),
    ]
)
