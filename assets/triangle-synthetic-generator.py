"""Build a synthetic reinsurance loss triangle and render bermuda's Altair views.

Shaped to match the terminal plugin demo: accident years 2018-2025, development
lags 12-96 months, a ragged lower-right edge from evaluations that haven't
happened yet, and paid age-to-age factors decaying toward 1.0.

Deliberately synthetic but domain-plausible: random numbers render fine but do
not read as real to anyone who knows the shape of a triangle.
"""

import datetime as dt
import json
import pathlib
import random

import altair as alt
from bermuda import Cell, Triangle
from bermuda.plot import (
    bermuda_plot_theme,
    plot_atas,
    plot_ballistic,
    plot_data_completeness,
    plot_heatmap,
)

random.seed(20260812)

OUT = pathlib.Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

FIRST_YEAR = 2018
LAST_YEAR = 2025
AS_OF = dt.date(2026, 6, 30)

# Cumulative proportion of ultimate at each 12-month development lag.
# Reported runs ahead of paid, and both converge toward 1.0.
PAID_PATTERN = [0.28, 0.52, 0.68, 0.79, 0.86, 0.91, 0.95, 0.98]
REPORTED_PATTERN = [0.55, 0.75, 0.86, 0.92, 0.955, 0.975, 0.99, 1.00]

cells = []
for offset, year in enumerate(range(FIRST_YEAR, LAST_YEAR + 1)):
    # Premium grows a few percent a year; loss ratio wanders around 65%.
    earned_premium = 10_000_000 * (1.045**offset) * random.uniform(0.97, 1.03)
    ultimate_loss_ratio = random.gauss(0.65, 0.045)
    ultimate_loss = earned_premium * ultimate_loss_ratio

    period_start = dt.date(year, 1, 1)
    period_end = dt.date(year, 12, 31)

    for lag_index, (paid_pct, reported_pct) in enumerate(
        zip(PAID_PATTERN, REPORTED_PATTERN)
    ):
        eval_year = year + lag_index + 1
        evaluation_date = dt.date(eval_year, 12, 31)
        # The ragged edge: evaluations that would fall in the future don't exist.
        if evaluation_date > AS_OF:
            break

        wobble = random.uniform(0.97, 1.03)
        paid_loss = ultimate_loss * paid_pct * wobble
        reported_loss = ultimate_loss * reported_pct * random.uniform(0.98, 1.02)
        # Reported can never sensibly sit below paid.
        reported_loss = max(reported_loss, paid_loss * 1.01)

        cells.append(
            Cell(
                period_start=period_start,
                period_end=period_end,
                evaluation_date=evaluation_date,
                values={
                    "earned_premium": round(earned_premium, 2),
                    "paid_loss": round(paid_loss, 2),
                    "reported_loss": round(reported_loss, 2),
                },
            )
        )

triangle = Triangle(cells)
print(f"cells: {len(triangle)}")
print(f"periods: {FIRST_YEAR}-{LAST_YEAR}, dev lags: {sorted(set(triangle.dev_lags()))}")

# Keep the data itself, so the terminal demo can be re-recorded from the same
# triangle and the two renderings are genuinely comparable.
(OUT / "triangle.json").write_text(triangle.to_json())
triangle.to_long_csv(str(OUT / "triangle.csv"))

# Sized to fit the ~740px content column on austinbrian.github.io once axis
# labels and legends are accounted for, stacked one per row.
WIDTH, HEIGHT = 360, 165

alt.theme.enable("default")

charts = {
    "heatmap": plot_heatmap(
        triangle, metric_spec=["Paid Loss"], width=WIDTH, height=HEIGHT
    ),
    "completeness": plot_data_completeness(
        triangle, width=WIDTH, height=HEIGHT
    ),
    "atas": plot_atas(
        triangle, metric_spec=["Paid ATA"], width=WIDTH, height=HEIGHT
    ),
    "ballistic": plot_ballistic(
        triangle,
        axis_metrics={
            "Paid Loss": lambda cell: cell["paid_loss"],
            "Reported Loss": lambda cell: cell["reported_loss"],
        },
        width=WIDTH,
        height=HEIGHT,
    ),
}

for name, chart in charts.items():
    chart.save(str(OUT / f"{name}.png"), ppi=140)
    print(f"rendered {name}")

def without_config(chart: alt.Chart) -> alt.Chart:
    """Subcharts cannot carry their own config inside a concat; it moves to the top."""
    chart = chart.copy()
    chart.config = alt.Undefined
    return chart


theme = bermuda_plot_theme()

combined = alt.vconcat(
    without_config(charts["heatmap"]),
    without_config(charts["completeness"]),
    without_config(charts["atas"]),
    without_config(charts["ballistic"]),
).resolve_scale(color="independent", size="independent")

# Altair's configure() validates bermuda's theme dict more strictly than Vega-Lite
# itself does, so write the config into the spec rather than through the API.
spec = json.loads(combined.to_json())
spec["config"] = theme["config"]
spec["autosize"] = theme.get("autosize", "pad")

# bermuda pads the ATA x scale by 10, which at this width renders a -10 tick and
# implies negative development lag. Clamp the domain to the lags that exist.
lags = sorted({float(lag) for lag in triangle.dev_lags()})
for layer in spec["vconcat"][2].get("layer", []):
    x_encoding = layer.get("encoding", {}).get("x")
    if x_encoding and x_encoding.get("field") == "dev_lag":
        x_encoding["scale"] = {"domain": [0, lags[-1] + 12], "nice": False}

(OUT / "combined.vg.json").write_text(json.dumps(spec, indent=1))

import vl_convert as vlc

(OUT / "combined.png").write_bytes(vlc.vegalite_to_png(json.dumps(spec), scale=2))
print("wrote combined.png and combined.vg.json")
