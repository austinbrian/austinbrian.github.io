import dash
from app.routers.layouts.hub_layout import layout as hub_layout

dash.register_page(
    __name__,
    path="/hub/",
    title="Running Hub",
    description="Main running hub page",
    redirect_from=["/hub"],
    layout=hub_layout,
)
