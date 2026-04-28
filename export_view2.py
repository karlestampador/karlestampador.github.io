"""
export_view2.py
---------------
Exports the NYC Airbnb Occupancy & Booking Analysis chart (View 2) to a
self-contained HTML file that can be dropped straight into the portfolio repo.

Run from the root of your project:
    python export_view2.py

Output: view2_occupancy_analysis.html
"""

import pandas as pd
import numpy as np
import altair as alt

# ── No vegafusion needed for HTML export ─────────────────────────────────────
alt.data_transformers.disable_max_rows()

# ── Portfolio colour palette ──────────────────────────────────────────────────
ROOM_TYPE_COLORS = {
    "Entire Home/Apt": "#1B3A6B",
    "Private Room":    "#5B8BE8",
    "Shared Room":     "#F0C040",
    "Hotel Room":      "#89A5DD",
}
ROOM_TYPE_ORDER = list(ROOM_TYPE_COLORS.keys())
COLOR_RANGE     = list(ROOM_TYPE_COLORS.values())

# Heatmap sequential: low booked nights → light, high → cobalt
HEATMAP_RANGE = ["#EEF2FB", "#C9D9F5", "#89A5DD", "#3B6BC8", "#1B3A6B", "#002452"]

# Bar chart: selected borough → cobalt, unselected → muted blue-grey
BAR_SELECTED   = "#1B3A6B"
BAR_UNSELECTED = "#A8BDDB"

# ── Load ──────────────────────────────────────────────────────────────────────
raw_data = pd.read_csv("../../../data/raw/Airbnb_Open_Data.csv")
raw_data.columns = [c.strip() for c in raw_data.columns]

# ── Clean ─────────────────────────────────────────────────────────────────────
for col in ["price", "service fee"]:
    raw_data[col] = (
        raw_data[col].astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .astype(float)
    )

# instant_bookable → bool
raw_data["instant_bookable"] = (
    raw_data["instant_bookable"].astype(str).str.lower()
    .map({"true": True, "t": True, "1": True, "yes": True, "y": True,
          "false": False, "f": False, "0": False, "no": False, "n": False})
    .fillna(False).astype(bool)
)

# host_identity_verified → bool
raw_data["host_identity_verified"] = (
    raw_data["host_identity_verified"].astype(str).str.lower()
    .map({"verified": True, "t": True, "true": True, "yes": True, "y": True,
          "unconfirmed": False, "false": False, "f": False, "no": False, "n": False})
    .fillna(False).astype(bool)
)

categorical_cols = [
    "id", "host id", "neighbourhood group", "neighbourhood", "country",
    "country code", "cancellation_policy", "room type", "host_identity_verified",
]
raw_data[categorical_cols] = raw_data[categorical_cols].astype("category")

numeric_cols = [
    "Construction year", "price", "service fee", "minimum nights",
    "number of reviews", "reviews per month",
    "calculated host listings count", "availability 365",
]
raw_data[numeric_cols] = raw_data[numeric_cols].apply(pd.to_numeric, errors="coerce")
raw_data["last review"] = pd.to_datetime(raw_data["last review"], errors="coerce")

raw_data = raw_data.dropna(subset=["Construction year"])
raw_data["Construction year"] = raw_data["Construction year"].astype(int)

# Outlier filters
raw_data = raw_data[(raw_data["minimum nights"] >= 0)                         & (raw_data["minimum nights"] < 40)]
raw_data = raw_data[(raw_data["number of reviews"] >= 0)                      & (raw_data["number of reviews"] < 400)]
raw_data = raw_data[(raw_data["reviews per month"] >= 0)                      & (raw_data["reviews per month"] < 50)]
raw_data = raw_data[(raw_data["calculated host listings count"] >= 1)         & (raw_data["calculated host listings count"] < 50)]
raw_data = raw_data[(raw_data["availability 365"] >= 0)                       & (raw_data["availability 365"] <= 365)]
raw_data = raw_data.dropna(subset=["neighbourhood group", "host_identity_verified", "cancellation_policy"])

# Borough name fixes
raw_data["neighbourhood group"] = (
    raw_data["neighbourhood group"].astype(str).str.strip().str.title()
    .replace({"Brookln": "Brooklyn", "Manhatan": "Manhattan"})
)
raw_data["room type"] = raw_data["room type"].astype(str).str.strip().str.title()

# Fix future last_review dates
_today = pd.to_datetime("2025-11-26")
raw_data.loc[raw_data["last review"] > _today, "last review"] = pd.NaT

# Derived columns
raw_data["availability 365"] = pd.to_numeric(raw_data["availability 365"], errors="coerce").fillna(0)
raw_data["booked_nights"]    = (365 - raw_data["availability 365"]).clip(lower=0, upper=365)
raw_data["occupancy_rate"]   = (raw_data["booked_nights"] / 365).clip(0, 1)
raw_data["demand_efficiency"] = raw_data["booked_nights"] / (raw_data["price"].replace({0: np.nan}) + 1e-9)

# Review score composite
if "review rate number" in raw_data.columns:
    raw_data["avg_review_score"] = pd.to_numeric(raw_data["review rate number"], errors="coerce")
else:
    r_month = pd.to_numeric(raw_data.get("reviews per month", pd.Series(0)), errors="coerce").fillna(0)
    r_count = pd.to_numeric(raw_data.get("number of reviews", pd.Series(0)), errors="coerce").fillna(0)
    raw_data["avg_review_score"] = (
        0.5 * (r_month - r_month.mean()) / (r_month.std() + 1e-9)
        + 0.5 * (r_count - r_count.mean()) / (r_count.std() + 1e-9)
    )

# Price tail trimming
raw_data = raw_data[raw_data["price"].notnull()].copy()
_low, _high = np.nanpercentile(raw_data["price"], [0.5, 99.5])
raw_data = raw_data[(raw_data["price"] >= max(1, _low)) & (raw_data["price"] <= _high)].copy()

raw_data["minimum nights"] = pd.to_numeric(raw_data["minimum nights"], errors="coerce").fillna(1).astype(int)
raw_data.loc[raw_data["minimum nights"] < 1, "minimum nights"] = 1
raw_data["id"] = raw_data["id"].astype(str)

# Final cleaned df + sample for scatter (keeps file size reasonable)
cleaned = raw_data.copy()
scatter_sample = cleaned.sample(n=4000, random_state=1).reset_index(drop=True)

# ── Selections ────────────────────────────────────────────────────────────────
brush = alt.selection_interval(encodings=["x", "y"], name="brush", empty="all")

neigh_click = alt.selection_point(
    fields=["neighbourhood group"],
    name="neigh_click",
    on="click",
    toggle=True,
    clear="dblclick",
    empty="all",
)

cell_sel = alt.selection_point(
    fields=["price_bin", "cancellation_policy"],
    name="cell_sel",
    on="click",
    toggle=True,
    clear="dblclick",
    empty="all",
)

BIN = alt.Bin(maxbins=6)

# ── Scatter: Price vs Booked Nights ──────────────────────────────────────────
scatter = (
    alt.Chart(scatter_sample)
    .transform_bin(as_="price_bin", field="price", bin=BIN)
    .mark_circle(size=55, opacity=0.75)
    .encode(
        x=alt.X("price:Q", title="Price ($/night)",
                axis=alt.Axis(format="$")),
        y=alt.Y("booked_nights:Q", title="Estimated Booked Nights"),
        color=alt.Color(
            "room type:N", title="Room Type",
            sort=ROOM_TYPE_ORDER,
            scale=alt.Scale(domain=ROOM_TYPE_ORDER, range=COLOR_RANGE),
        ),
        opacity=alt.condition(neigh_click, alt.value(0.8), alt.value(0.08)),
        tooltip=[
            alt.Tooltip("price:Q",              format="$,.0f",  title="Price"),
            alt.Tooltip("booked_nights:Q",                        title="Booked Nights"),
            alt.Tooltip("room type:N",                            title="Room Type"),
            alt.Tooltip("neighbourhood group:N",                  title="Borough"),
            alt.Tooltip("price_bin:O",                            title="Price Bin"),
        ],
    )
    .transform_filter(cell_sel)
    .add_params(brush, neigh_click)
    .properties(
        width=480,
        height=300,
        title=alt.TitleParams(
            "Price vs Estimated Booked Nights",
            subtitle="Brush to select · click bar chart to filter by borough",
            anchor="middle", fontSize=14, subtitleFontSize=11,
            subtitleColor="#6B7280",
        ),
    )
)

# ── Bar chart: Average Occupancy Rate by Borough ──────────────────────────────
bar_chart = (
    alt.Chart(cleaned)
    .transform_bin(as_="price_bin", field="price", bin=BIN)
    .transform_filter(brush)
    .transform_filter(cell_sel)
    .transform_aggregate(
        avg_occupancy="mean(occupancy_rate)",
        groupby=["neighbourhood group"],
    )
    .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
    .encode(
        x=alt.X("avg_occupancy:Q", title="Average Occupancy Rate",
                axis=alt.Axis(format=".0%")),
        y=alt.Y("neighbourhood group:N", sort="-x", title="Borough"),
        color=alt.condition(
            neigh_click,
            alt.value(BAR_SELECTED),
            alt.value(BAR_UNSELECTED),
        ),
        opacity=alt.condition(brush, alt.value(1.0), alt.value(0.3)),
        tooltip=[
            alt.Tooltip("neighbourhood group:N", title="Borough"),
            alt.Tooltip("avg_occupancy:Q", format=".1%", title="Avg Occupancy"),
        ],
    )
    .add_params(neigh_click)
    .properties(
        width=480,
        height=240,
        title=alt.TitleParams(
            "Average Occupancy Rate by Borough",
            subtitle="Click a bar to highlight that borough in the scatter",
            anchor="middle", fontSize=14, subtitleFontSize=11,
            subtitleColor="#6B7280",
        ),
    )
)

# ── Heatmap: Median Booked Nights by Price Bin × Cancellation Policy ──────────
heatmap = (
    alt.Chart(cleaned)
    .transform_filter(neigh_click)
    .transform_filter(brush)
    .transform_bin(as_="price_bin", field="price", bin=BIN)
    .transform_aggregate(
        median_booked="median(booked_nights)",
        count_listings="count()",
        groupby=["cancellation_policy", "price_bin"],
    )
    .transform_filter("datum.median_booked != null")
    .mark_rect()
    .encode(
        x=alt.X("price_bin:O", title="Price (binned, $/night)"),
        y=alt.Y(
            "cancellation_policy:N",
            title="Cancellation Policy",
            sort=["Strict", "Moderate", "Flexible"],
        ),
        color=alt.Color(
            "median_booked:Q",
            title="Median Booked Nights",
            scale=alt.Scale(range=HEATMAP_RANGE),
            legend=alt.Legend(format=".0f"),
        ),
        tooltip=[
            alt.Tooltip("price_bin:O",          title="Price Bin"),
            alt.Tooltip("cancellation_policy:N", title="Cancellation Policy"),
            alt.Tooltip("median_booked:Q",       title="Median Booked Nights", format=".1f"),
            alt.Tooltip("count_listings:Q",      title="Listings in Cell"),
        ],
        stroke=alt.condition(cell_sel, alt.value("#F0C040"), alt.value("transparent")),
        strokeWidth=alt.condition(cell_sel, alt.value(2.5), alt.value(0)),
        opacity=alt.condition(cell_sel, alt.value(1.0), alt.value(0.85)),
    )
    .add_params(cell_sel)
    .properties(
        width=750,
        height=520,
        title=alt.TitleParams(
            "Median Booked Nights: Price Tier × Cancellation Policy",
            subtitle="Click a cell to cross-filter the scatter & bar · brush scatter to filter here",
            anchor="middle", fontSize=14, subtitleFontSize=11,
            subtitleColor="#6B7280",
        ),
    )
)

# ── Compose ───────────────────────────────────────────────────────────────────
right_col = alt.vconcat(scatter, bar_chart, spacing=24).resolve_scale(color="independent")

view = (
    alt.hconcat(heatmap, right_col, spacing=36)
    .resolve_scale(color="independent")
    .properties(
        title=alt.TitleParams(
            "NYC Airbnb — Occupancy & Booking Analysis",
            subtitle="All three charts are linked: brush, click, and filter interact across views",
            anchor="middle", fontSize=18, subtitleFontSize=13,
            subtitleColor="#6B7280",
        )
    )
    .configure_axis(
        labelFontSize=11, titleFontSize=13,
        gridColor="#E5E7EB", domainColor="#D1D5DB",
    )
    .configure_legend(labelFontSize=11, titleFontSize=12)
    .configure_title(fontSize=16, anchor="middle")
    .configure_view(strokeOpacity=0)
)

# ── Save ──────────────────────────────────────────────────────────────────────
OUT = "view2_occupancy_analysis.html"
view.save(OUT)
print(f"Saved → {OUT}")