import dash
from app.routers.layouts.individual_runs_layout import layout as individual_runs_layout

dash.register_page(
    __name__,
    path="/run-log/",
    title="Run Log",
    description="Run log",
    redirect_from=["/run-log"],
    layout=individual_runs_layout,
)
