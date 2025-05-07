from app.routers.layouts.cumulative_total_layout import (
    layout as cumulative_total_layout,
)
from app.routers.layouts.individual_runs_layout import layout as individual_runs_layout
from app.routers.layouts.pace_analysis_layout import layout as pace_analysis_layout

__all__ = [
    "cumulative_total_layout",
    "individual_runs_layout",
    "pace_analysis_layout",
]
