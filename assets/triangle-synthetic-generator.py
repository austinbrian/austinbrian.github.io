"""Build a synthetic reinsurance loss triangle and render bermuda's Altair views.

Quarterly experience periods on quarterly evaluations, which is the shape most
real triangles arrive in and the shape the plugin demo shows. An annual 7x7
grid is too thin to read as a triangle in either renderer.

Two properties matter for the plots to say anything:

  * a ragged lower-right edge, from evaluations that have not happened yet
  * ragged *fields*, not just ragged cells. Claim counts start arriving partway
    through, so completeness has something to encode - with a uniform field
    count that plot is one flat colour and carries no information.

Deliberately synthetic but domain-plausible: random numbers render fine but do
not read as real to anyone who knows the shape of a triangle.

Outputs, all copied into /assets and served by the site:
    triangle.json / triangle.csv  the data, so the terminal demo can be
                                  re-recorded against the same triangle
    combined.png                  static fallback for the noscript case

Running it
----------
bermuda's own checkout venv is missing dependencies, and bermuda calls
`np.NaN`, removed in NumPy 2, so it needs the pins its pyproject already
declares. Build an isolated environment rather than repairing that one:

    uv venv bermudaenv --python 3.12
    UV_INDEX_URL=https://pypi.org/simple uv pip install \
        --python bermudaenv/bin/python \
        ~/ldgr/bermuda-ledger/dist/bermuda_ledger-*.whl \
        vl-convert-python "numpy<2" "scipy<1.14" "pandas<2.3"
    ./bermudaenv/bin/python triangle-synthetic-generator.py

UV_INDEX_URL is needed because the default pip config points at Ledger's
CodeArtifact, which 401s for public packages.
"""

import datetime as dt
import json
import pathlib
import random

from bermuda import Cell, Triangle

random.seed(20260812)

OUT = pathlib.Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

FIRST_PERIOD = (2023, 1)   # 2023Q1
N_PERIODS = 12             # through 2025Q4
N_LAGS = 12                # quarterly dev lags, 3..36 months
AS_OF = dt.date(2026, 6, 30)

# Claim counts only start arriving at evaluations from here on, so completeness
# shows a diagonal band rather than a solid block.
CLAIM_COUNTS_FROM = dt.date(2025, 1, 1)

# Cumulative share of ultimate at each quarterly lag. Reported leads paid and
# both converge on 1.0, so age-to-age factors decay toward 1.0.
PAID_PATTERN = [0.10, 0.22, 0.34, 0.45, 0.55, 0.63,
                0.71, 0.78, 0.84, 0.89, 0.93, 0.96]
REPORTED_PATTERN = [0.32, 0.48, 0.60, 0.69, 0.76, 0.82,
                    0.87, 0.91, 0.94, 0.965, 0.98, 0.99]


def quarter_start(index: int) -> dt.date:
    year, quarter = FIRST_PERIOD
    total = (year * 4 + quarter - 1) + index
    return dt.date(total // 4, (total % 4) * 3 + 1, 1)


def quarter_end(start: dt.date) -> dt.date:
    month = start.month + 2
    last = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if month == 2 and start.year % 4 == 0:
        last = 29
    return dt.date(start.year, month, last)


def add_months(date: dt.date, months: int) -> dt.date:
    total = date.year * 12 + (date.month - 1) + months
    year, month = divmod(total, 12)
    last = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    if month == 1 and year % 4 == 0:
        last = 29
    return dt.date(year, month + 1, last)


cells = []
for index in range(N_PERIODS):
    period_start = quarter_start(index)
    period_end = quarter_end(period_start)

    earned_premium = 12_000_000 * (1.02**index) * random.uniform(0.94, 1.06)
    ultimate_loss_ratio = random.gauss(0.64, 0.05)
    ultimate_loss = earned_premium * ultimate_loss_ratio
    ultimate_claims = earned_premium / random.uniform(21_000, 26_000)

    for lag_index in range(N_LAGS):
        lag_months = (lag_index + 1) * 3
        evaluation_date = add_months(period_end, lag_months)
        # The ragged edge: evaluations that would fall in the future don't exist.
        if evaluation_date > AS_OF:
            break

        paid_pct = PAID_PATTERN[lag_index]
        reported_pct = REPORTED_PATTERN[lag_index]
        paid = ultimate_loss * paid_pct * random.uniform(0.97, 1.03)
        reported = ultimate_loss * reported_pct * random.uniform(0.98, 1.02)
        reported = max(reported, paid * 1.02)

        values = {
            "earned_premium": round(earned_premium, 2),
            "paid_loss": round(paid, 2),
            "reported_loss": round(reported, 2),
        }

        # Claim counts only from the evaluations where the cedent began
        # supplying them.
        if evaluation_date >= CLAIM_COUNTS_FROM:
            reported_claims = ultimate_claims * reported_pct * random.uniform(0.96, 1.04)
            # Claims close as the period develops, so the open share falls.
            open_share = max(0.04, 0.62 * (1 - paid_pct) ** 1.1)
            values["reported_claims"] = round(reported_claims, 1)
            values["open_claims"] = round(reported_claims * open_share, 1)

        cells.append(
            Cell(
                period_start=period_start,
                period_end=period_end,
                evaluation_date=evaluation_date,
                values=values,
            )
        )

triangle = Triangle(cells)
field_counts = sorted({len(cell.values) for cell in triangle})
print(f"cells: {len(triangle)} of {N_PERIODS * N_LAGS} possible")
print(f"dev lags: {sorted(set(triangle.dev_lags()))}")
print(f"fields per cell: {field_counts}")

(OUT / "triangle.json").write_text(triangle.to_json())
triangle.to_long_csv(str(OUT / "triangle.csv"))
print("wrote triangle.json and triangle.csv")
