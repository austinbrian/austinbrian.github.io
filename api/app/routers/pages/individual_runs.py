from datetime import date

import dash
from app.routers.layouts.individual_runs_layout import layout as individual_runs_layout
from dash import dcc

store_layout = dcc.Store(
    id="individual-runs-date-range-store",
    data={
        "start_date": date(date.today().year, 1, 1).isoformat(),
        "end_date": date(date.today().year, 12, 31).isoformat(),
    },
)


dash.register_page(
    __name__,
    path="/log/",
    title="Run Log",
    description="Weekly run log",
    redirect_from=["/log"],
    layout=[store_layout, individual_runs_layout],
)
