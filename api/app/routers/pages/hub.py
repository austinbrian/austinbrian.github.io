import dash
from app.routers.layouts.hub_layout import layout as hub_layout

dash.register_page(
    __name__,
    path="/hub/",
    title="Hub",
    description="Main hub page",
    redirect_from=["/hub"],
    layout=hub_layout,
)
