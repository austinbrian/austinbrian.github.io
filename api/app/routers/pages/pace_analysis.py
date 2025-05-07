import dash
from app.routers.layouts.pace_analysis_layout import layout as pace_analysis_layout

dash.register_page(
    __name__,
    path="/pace-analysis/",
    title="Pace Analysis",
    description="Pace analysis",
    redirect_from=["/pace-analysis"],
    layout=pace_analysis_layout,
)
