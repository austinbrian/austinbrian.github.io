from datetime import date

import dash
from app.routers.layouts.pace_analysis_layout import layout as pace_analysis_layout
from dash import dcc

store_layout = dcc.Store(
    id="pace-analysis-date-range-store",
    data={
        "start_date": date(date.today().year, 1, 1).isoformat(),
        "end_date": date(date.today().year, 12, 31).isoformat(),
    },
)
dash.register_page(
    __name__,
    path="/pace-analysis/",
    title="Pace Analysis",
    description="Pace analysis",
    redirect_from=["/pace-analysis"],
    layout=[store_layout, pace_analysis_layout],
)
