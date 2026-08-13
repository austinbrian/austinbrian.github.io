"""Render every view the terminal plugin offers, as Vega-Lite specs.

Reads the synthetic triangle already committed to the site and writes one
combined JSON keyed by view, which the landing page's selector embeds one at a
time. Grouping and order mirror the plugin's own tabs.

See triangle-synthetic-generator.py for how the triangle itself is built and
for the environment this needs.
"""

import json
import pathlib

import altair as alt
from bermuda import Triangle
from bermuda.plot import (
    bermuda_plot_theme,
    plot_atas,
    plot_ballistic,
    plot_data_completeness,
    plot_growth_curve,
    plot_heatmap,
    plot_mountain,
    plot_right_edge,
    plot_sunset,
)

SITE = pathlib.Path("/Users/austinbrian/dev/austinbrian.github.io")
OUT = pathlib.Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# Sized to fit the site's ~740px content column once axis labels and legends
# are accounted for.
WIDTH, HEIGHT = 380, 200

triangle = Triangle.from_json(str(SITE / "assets" / "triangle-synthetic.json"))

# group / label / builder, in the order the plugin presents them.
VIEWS = [
    ("Shape & coverage", "heatmap", "Paid loss heatmap",
     lambda t: plot_heatmap(t, metric_spec=["Paid Loss"], width=WIDTH, height=HEIGHT)),
    ("Shape & coverage", "completeness", "Data completeness",
     lambda t: plot_data_completeness(t, width=WIDTH, height=HEIGHT)),
    ("Shape & coverage", "right_edge", "Right edge",
     lambda t: plot_right_edge(t, width=WIDTH, height=HEIGHT)),
    ("Development", "atas", "Paid ATAs",
     lambda t: plot_atas(t, metric_spec=["Paid ATA"], width=WIDTH, height=HEIGHT)),
    ("Development", "growth_curve", "Growth curve",
     lambda t: plot_growth_curve(t, metric_spec=["Paid Loss Ratio"], width=WIDTH, height=HEIGHT)),
    ("Development", "sunset", "Sunset",
     lambda t: plot_sunset(t, metric_spec=["Paid Loss"], width=WIDTH, height=HEIGHT)),
    ("More views", "mountain", "Mountain",
     lambda t: plot_mountain(t, metric_spec=["Paid Loss Ratio"], width=WIDTH, height=HEIGHT)),
    ("More views", "ballistic", "Ballistic (paid vs reported)",
     lambda t: plot_ballistic(
         t,
         axis_metrics={
             "Paid Loss": lambda cell: cell["paid_loss"],
             "Reported Loss": lambda cell: cell["reported_loss"],
         },
         width=WIDTH,
         height=HEIGHT,
     )),
]

alt.theme.enable("default")
theme = bermuda_plot_theme()
lags = sorted({float(lag) for lag in triangle.dev_lags()})


def clamp_dev_lag_axis(spec: dict) -> None:
    """bermuda pads dev-lag scales by 10, which renders a negative-lag tick.

    Only continuous axes: heatmap and completeness encode dev_lag as nominal,
    and forcing a numeric domain on a band scale collapses their cells into
    full-width bars.
    """
    def walk(node):
        if isinstance(node, dict):
            x = node.get("encoding", {}).get("x")
            if (isinstance(x, dict) and x.get("field") == "dev_lag"
                    and x.get("type") == "quantitative"):
                x["scale"] = {"domain": [0, lags[-1] + 12], "nice": False}
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(spec)


views = {}
for group, key, label, build in VIEWS:
    chart = build(triangle)
    spec = json.loads(chart.to_json())
    # Altair validates bermuda's theme dict more strictly than Vega-Lite does,
    # so the config goes into the spec rather than through configure().
    spec["config"] = theme["config"]
    spec["autosize"] = theme.get("autosize", "pad")
    clamp_dev_lag_axis(spec)
    views[key] = {"group": group, "label": label, "spec": spec}
    print(f"  {group:18s} {key:14s} {len(json.dumps(spec)) // 1024}KB")

payload = {"order": [key for _, key, _, _ in VIEWS], "views": views}
(OUT / "triangle-views.json").write_text(json.dumps(payload))
size_kb = len(json.dumps(payload)) // 1024
print(f"wrote triangle-views.json ({size_kb}KB, {len(views)} views)")

# Static fallback for the noscript case: the first view.
import vl_convert as vlc

(OUT / "triangle-views-fallback.png").write_bytes(
    vlc.vegalite_to_png(json.dumps(views["heatmap"]["spec"]), scale=2)
)
print("wrote triangle-views-fallback.png")
