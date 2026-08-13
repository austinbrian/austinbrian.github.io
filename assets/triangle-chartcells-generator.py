"""Draw the synthetic triangle with the plugin's own terminal renderer.

Converts assets/triangle-synthetic.json into korra's ChartCellData shape and
runs termviz over every view the v2 demo offers, so the terminal and browser
renderings can be compared on identical data.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / "ldgr/korra-plugins/plugins/korra/renderers"))
import termviz  # noqa: E402

SITE = pathlib.Path("/Users/austinbrian/dev/austinbrian.github.io")
raw = json.loads((pathlib.Path(__file__).parent / "out" / "triangle.json").read_text())

VIEWS = ["heatmap", "completeness", "right_edge", "atas",
         "growth_curve", "sunset", "mountain", "ballistic"]


def months_between(start: str, end: str) -> int:
    sy, sm, _ = (int(p) for p in start.split("-"))
    ey, em, _ = (int(p) for p in end.split("-"))
    return (ey - sy) * 12 + (em - sm)


def field(value, unit="", label=""):
    return {"metric": value, "unit": unit, "field": label}


cells_in = raw["slices"][0]["cells"]

# paidAta needs the next evaluation of the same period, so index first.
by_period: dict[str, dict[int, dict]] = {}
for cell in cells_in:
    # bermuda measures development from period END, so 2018-12-31 evaluated
    # 2019-12-31 is a 12-month lag, not 23.
    lag = months_between(cell["period_end"], cell["evaluation_date"])
    by_period.setdefault(cell["period_start"], {})[lag] = cell

chart_cells = []
for period_start, lags in sorted(by_period.items()):
    for lag, cell_in in sorted(lags.items()):
        values = cell_in["values"]
        premium = values["earned_premium"]
        paid = values["paid_loss"]
        reported = values["reported_loss"]
        next_cell = lags.get(lag + 12)
        next_paid = next_cell["values"]["paid_loss"] if next_cell else None

        cell = {
            "periodStart": period_start,
            "evaluationDate": cell_in["evaluation_date"],
            "devLag": lag,
            "experienceResolution": 3,   # quarterly periods
            "evaluationResolution": 3,
            "paidLoss": field(paid, "USD", "Paid Loss"),
            "reportedLoss": field(reported, "USD", "Reported Loss"),
            "earnedPremium": field(premium, "USD", "Earned Premium"),
            "paidLossRatio": field(100 * paid / premium, "%", "Paid LR"),
            "reportedLossRatio": field(100 * reported / premium, "%", "Reported LR"),
            "paidAta": field(
                next_paid / paid if next_paid and paid else None, "", "Paid ATA"
            ),
        }
        for name, key in (("reportedClaims", "reported_claims"),
                          ("openClaims", "open_claims")):
            if key in values:
                cell[name] = field(values[key], "N", name)
        cell["fields"] = [k for k in ("paidLoss", "reportedLoss", "earnedPremium",
                                      "reportedClaims", "openClaims")
                          if isinstance(cell.get(k), dict)
                          and cell[k]["metric"] is not None]
        chart_cells.append(cell)

print(f"{len(chart_cells)} chart cells, "
      f"metrics present: {sorted(termviz.present_metrics(chart_cells))}\n")
print(f"views this triangle supports: {termviz.available_views(chart_cells)}\n")

out_dir = pathlib.Path(__file__).parent / "out"
out_dir.mkdir(exist_ok=True)
plain_parts, ansi_parts = [], []

for view in VIEWS:
    try:
        plain = termviz.render(chart_cells, view, color=False, width=72,
                               nav=False, triangle="synthetic 2018-2025")
        ansi = termviz.render(chart_cells, view, color=True, width=72,
                              nav=False, triangle="synthetic 2018-2025")
    except termviz.UnsupportedView as error:
        plain = ansi = f"\n[{view}] unavailable: {error}"
    plain_parts.append(plain)
    ansi_parts.append(ansi)
    print(plain)

(out_dir / "terminal_views.txt").write_text("\n".join(plain_parts))
(out_dir / "terminal_views.ansi").write_text("\n".join(ansi_parts))
