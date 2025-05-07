from datetime import date

from dash import dcc

layout = dcc.Store(
    id="date-range-store",
    data={
        "start_date": date(date.today().year, 1, 1).isoformat(),
        "end_date": date(date.today().year, 12, 31).isoformat(),
    },
)
