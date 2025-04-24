import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html


def cumulative_total(data: dict = None) -> go.Figure:
    if not data:
        return dcc.NoUpdate

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["date"], y=data["total"], mode="lines+markers"))
    fig.update_layout(title="Cumulative Total", xaxis_title="Date", yaxis_title="Total")
    return fig


def info_box(data: dict = None) -> html.Div:
    if not data:
        return dcc.NoUpdate

    # Build table rows for each data point
    rows = [
        html.Tr([html.Td(d), html.Td(t)]) for d, t in zip(data["date"], data["total"])
    ]

    # Create a Bootstrap table
    table = dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Date"), html.Th("Total")])),
            html.Tbody(rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
    )

    # Wrap the table in an info card
    return dbc.Card(
        [
            dbc.CardHeader("Cumulative Total Data"),
            dbc.CardBody(table),
        ],
        style={
            "margin": "10px 0",
            "maxHeight": "300px",
            "overflowY": "auto",
        },
    )
