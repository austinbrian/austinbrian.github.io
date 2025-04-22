import dash

dash.register_page(
    __name__,
    path="/",
    title="Home",
    description="Home page",
    redirect_from=["/"],
)

layout = []
