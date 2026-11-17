"""Interactive Streamlit dashboard: Nassau Candy product-line profitability."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analytics import (
    CLEAN_DATA_PATH, DIVISION_COLORS, FACTORY_COORDS, OUTPUT_DIR, PRODUCT_FACTORY, ROOT,
    RAW_DATA_CANDIDATES, concentration_metrics, division_metrics, factory_metrics, load_and_clean, monthly_metrics,
    pareto_table, portfolio_kpis, product_metrics, risk_register, summarize,
)

st.set_page_config(
    page_title="Nassau Candy | Profitability Intelligence",
    page_icon="🍬",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#14213D"
TEAL = "#168AAD"
GREEN = "#2D6A4F"
GOLD = "#E9A23B"
ROSE = "#B54771"
SLATE = "#5B6573"

st.markdown(
    """
    <style>
      .stApp { background: #F4F8FA; }
      .block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1500px; }
      .hero {
        background: linear-gradient(115deg, #14213D 0%, #19445A 58%, #168AAD 100%);
        border-radius: 16px; padding: 24px 28px; color: white; margin-bottom: 14px;
        box-shadow: 0 8px 22px rgba(20,33,61,.16);
      }
      .hero h1 { font-size: 1.85rem; margin: 0 0 6px 0; color: white; font-weight: 750; }
      .hero p { margin: 0; color: #D9E9EF; font-size: .96rem; }
      .hero .tag { display: inline-block; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.22);
                   border-radius: 20px; padding: 3px 10px; font-size: .75rem; letter-spacing: .04em; margin-bottom: 10px; }
      .metric-card { background: white; border: 1px solid #DDE7EB; border-radius: 12px; padding: 12px 13px 11px 13px;
                     box-shadow: 0 3px 10px rgba(20,33,61,.06); min-height: 94px; margin-bottom: 8px; }
      .metric-card .label { color: #5B6573; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; font-weight: 700; }
      .metric-card .value { color: #14213D; font-size: 1.42rem; font-weight: 750; margin-top: 5px; line-height: 1.1; }
      .metric-card .sub { color: #5B6573; font-size: .75rem; margin-top: 5px; }
      div[data-testid="stTabs"] button { font-weight: 650; color: #14213D; }
      div[data-testid="stSidebar"] { background: #EAF1F4; }
      .small-note { color: #5B6573; font-size: .82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_dashboard_data() -> tuple[pd.DataFrame, dict]:
    report_path = OUTPUT_DIR / "data_quality_report.json"
    report = None

    if CLEAN_DATA_PATH.is_file():
        df = pd.read_csv(CLEAN_DATA_PATH, parse_dates=["order_date", "ship_date", "month"])
        df["postal_code"] = df["postal_code"].astype("string")
    else:
        source_path = next((path for path in RAW_DATA_CANDIDATES if path.is_file()), None)
        if source_path is None:
            raise FileNotFoundError(
                f"Neither the cleaned dataset ({CLEAN_DATA_PATH}) nor a source CSV "
                f"({', '.join(str(path) for path in RAW_DATA_CANDIDATES)}) is available. "
                "Include one of these data files in the deployed repository."
            )
        df, report = load_and_clean(source_path)

    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    elif report is None:
        source_path = next((path for path in RAW_DATA_CANDIDATES if path.is_file()), None)
        if source_path is not None:
            _, report = load_and_clean(source_path)
        else:
            ship_days = pd.to_numeric(df["ship_days"], errors="coerce").dropna()
            order_id_year = pd.to_numeric(
                df["order_id"].astype("string").str.extract(r"^[A-Z]{2}-(\d{4})-", expand=False),
                errors="coerce",
            )
            report = {
                "source_file": str(CLEAN_DATA_PATH),
                "clean_rows": int(len(df)),
                "ship_days_min": float(ship_days.min()),
                "ship_days_median": float(ship_days.median()),
                "ship_days_max": float(ship_days.max()),
                "order_id_year_mismatch_rows": int((order_id_year != df["order_date"].dt.year).sum()),
                "validation_note": "Derived from cleaned data; source validation report was unavailable.",
            }

    return df, report


@st.cache_data(show_spinner=False)
def read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def money(value: float, decimals: int = 0) -> str:
    if pd.isna(value):
        return "—"
    return f"${value:,.{decimals}f}"


def pct(value: float, decimals: int = 1) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:.{decimals}f}%"


def num(value: float, decimals: int = 2) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}"


def short_label(name: str) -> str:
    return name.replace("Wonka Bar - ", "")


def card(label: str, value: str, sub: str, accent: str) -> None:
    st.markdown(
        f"""<div class="metric-card" style="border-top:4px solid {accent};">
              <div class="label">{label}</div><div class="value">{value}</div><div class="sub">{sub}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def style_fig(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=55, b=22),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=11.5, color=NAVY),
        title=dict(font=dict(size=15, color=NAVY), x=0.02, xanchor="left"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                    bgcolor="rgba(255,255,255,0)", font=dict(size=10)),
        hoverlabel=dict(bgcolor="white", font_size=11, font_color=NAVY),
    )
    fig.update_xaxes(gridcolor="#E6EDF0", zeroline=False, linecolor="#C9D6DC")
    fig.update_yaxes(gridcolor="#E6EDF0", zeroline=False, linecolor="#C9D6DC")
    return fig


def show(fig: go.Figure, height: int = 420) -> None:
    st.plotly_chart(style_fig(fig, height), width="stretch",
                    config={"displayModeBar": False, "responsive": True})


def table(frame: pd.DataFrame, height: int | None = None) -> None:
    options: dict = {"hide_index": True, "width": "stretch"}
    if height is not None:
        options["height"] = height
    st.dataframe(frame, **options)


def formatted_products(products: pd.DataFrame) -> pd.DataFrame:
    cols = ["product_name", "division", "revenue", "gross_profit", "gross_margin_pct",
            "profit_per_unit", "revenue_share_pct", "profit_share_pct", "cost_ratio_pct",
            "margin_volatility_pp", "classification"]
    out = products[cols].copy()
    for col, fn in {
        "revenue": lambda v: money(v, 2), "gross_profit": lambda v: money(v, 2),
        "gross_margin_pct": lambda v: pct(v, 2), "profit_per_unit": lambda v: money(v, 2),
        "revenue_share_pct": lambda v: pct(v, 2), "profit_share_pct": lambda v: pct(v, 2),
        "cost_ratio_pct": lambda v: pct(v, 2), "margin_volatility_pp": lambda v: num(v, 2) + " pp",
    }.items():
        out[col] = out[col].map(fn)
    out.columns = ["Product", "Division", "Revenue", "Gross profit", "Margin", "Profit/unit",
                   "Rev. share", "Profit share", "Cost ratio", "Volatility", "Classification"]
    return out


def pareto_figure(products: pd.DataFrame, metric: str, label: str) -> go.Figure:
    q = pareto_table(products, metric)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = [DIVISION_COLORS.get(v, SLATE) for v in q["division"]]
    fig.add_trace(
        go.Bar(x=q["product_name"].map(short_label), y=q[metric], name=label,
               marker_color=colors,
               customdata=np.stack([q["division"], q["gross_margin_pct"], q["revenue_share_pct"]], axis=-1),
               hovertemplate="<b>%{x}</b><br>" + label + ": $%{y:,.0f}<br>Division: %{customdata[0]}<br>Margin: %{customdata[1]:.1f}%<extra></extra>"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=q["product_name"].map(short_label), y=q["cumulative_pct"],
                   name="Cumulative %", mode="lines+markers", marker=dict(size=5, color=NAVY),
                   line=dict(color=NAVY, width=2),
                   hovertemplate="%{x}<br>Cumulative: %{y:.1f}%<extra></extra>"),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(x=[q["product_name"].map(short_label).iloc[0], q["product_name"].map(short_label).iloc[-1]],
                   y=[80, 80], name="80% line", mode="lines",
                   line=dict(color=ROSE, width=1.4, dash="dash"), hoverinfo="skip"),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="USD", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative share", range=[0, 105], ticksuffix="%", secondary_y=True)
    fig.update_xaxes(tickangle=55, tickfont=dict(size=9))
    fig.update_layout(title=f"{label} Pareto — ranked product contribution", barmode="overlay")
    return fig


def download_button(label: str, path: Path, mime: str, key: str) -> None:
    if path.exists():
        st.download_button(label, data=read_bytes(str(path)), file_name=path.name, mime=mime,
                           width="stretch", key=key)


# ---------------------------------------------------------------------------
# Sidebar and scope
# ---------------------------------------------------------------------------
raw, report = load_dashboard_data()
min_date, max_date = raw["order_date"].min().date(), raw["order_date"].max().date()

st.sidebar.markdown("## Filter the analysis")
date_range = st.sidebar.date_input(
    "Order date range", value=(min_date, max_date), min_value=min_date, max_value=max_date,
    help="Filters all modules by commercial demand date.",
)
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select both a start and an end date to view the dashboard.")
    st.stop()
start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])

division_options = sorted(raw["division"].dropna().unique())
selected_divisions = st.sidebar.multiselect("Division", division_options, default=division_options)
if not selected_divisions:
    st.warning("Select at least one division.")
    st.stop()

search = st.sidebar.text_input("Product search", placeholder="Name or Product ID…", help="Case-insensitive text match.")
benchmark_pct = st.sidebar.slider(
    "Margin threshold / benchmark", min_value=0, max_value=90, value=60, step=1, format="%d%%",
    help="Sets the risk benchmark. Optionally restrict all charts to products at or above it.",
)
benchmark = benchmark_pct / 100
restrict = st.sidebar.checkbox(
    "Only include products at/above benchmark", value=False,
    help="When off, the slider highlights risk but does not exclude products.",
)

scope_base = raw[
    raw["order_date"].between(start_date, end_date)
    & raw["division"].isin(selected_divisions)
].copy()
if search.strip():
    term = search.strip()
    scope_base = scope_base[
        scope_base["product_name"].str.contains(term, case=False, na=False, regex=False)
        | scope_base["product_id"].str.contains(term, case=False, na=False, regex=False)
    ].copy()
if scope_base.empty:
    st.warning("No order lines match these filters. Widen the date range, division selection or product search.")
    st.stop()

products_all = product_metrics(scope_base, benchmark)
below_count = int(products_all["below_benchmark"].sum())
if restrict:
    eligible = set(products_all.loc[~products_all["below_benchmark"], "product_name"])
    scope = scope_base[scope_base["product_name"].isin(eligible)].copy()
    if scope.empty:
        st.warning("No products meet the selected margin benchmark. Lower the threshold or turn off the restriction.")
        st.stop()
    products = product_metrics(scope, benchmark)
else:
    scope = scope_base
    products = products_all

divisions = division_metrics(scope)
regions = summarize(scope, ["region"]).sort_values("revenue", ascending=False)
states = summarize(scope, ["state"])
states["order_line_share_pct"] = 100 * states["order_lines"] / states["order_lines"].sum()
states = states.sort_values("revenue", ascending=False)
factories = factory_metrics(scope)
monthly = monthly_metrics(scope)
risks = risk_register(products_all)
conc = concentration_metrics(products)
k = portfolio_kpis(scope, products)
portfolio_margin = k["gross_margin_pct"]

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"**Current scope:** {num(k['order_lines'],0)} lines · {k['products']} products · "
    f"{below_count} below benchmark"
)
st.sidebar.caption(
    "The risk register always evaluates the full date/division/search scope so low-margin products remain visible."
)
st.sidebar.download_button(
    "Download filtered order lines", data=scope.to_csv(index=False).encode("utf-8"),
    file_name="nassau_filtered_order_lines.csv", mime="text/csv", width="stretch",
)

# ---------------------------------------------------------------------------
# Header and KPIs
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <div class="tag">PRODUCT LINE PROFITABILITY · LIVE ANALYTICS</div>
      <h1>Nassau Candy Distributor — Margin Performance Intelligence</h1>
      <p>Profit contribution, division efficiency, cost diagnostics and portfolio dependency across 15 products.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(6)
with cols[0]: card("Revenue", money(k["revenue"], 0), f"{num(k['order_lines'],0)} order lines", TEAL)
with cols[1]: card("Gross profit", money(k["gross_profit"], 0), f"{money(k['profit_per_unit'],2)} per unit", GREEN)
with cols[2]: card("Weighted margin", pct(portfolio_margin, 2), f"Cost ratio {pct(k['cost_ratio_pct'],2)}", NAVY)
with cols[3]: card("Top-5 profit share", pct(k.get("top5_profit_share_pct", 0), 1), "Dependency indicator", GOLD)
with cols[4]: card("Products below benchmark", f"{below_count}/{len(products_all)}", f"{benchmark_pct}% threshold", ROSE)
with cols[5]: card("Period", f"{start_date.date():%b %Y} – {end_date.date():%b %Y}", f"{k['orders']:,} orders", SLATE)

st.caption(
    "Gross profit = Sales − Cost as supplied. This is gross margin, not net profit. "
    "Ship dates are excluded from operational KPIs because the source implies multi-year lags."
)

tabs = st.tabs([
    "📊 Product overview", "🏢 Divisions", "⚠️ Cost & risk", "🎯 Concentration",
    "🗺️ Geography & factories", "📄 Executive brief", "🔧 Methods & data",
])

# ---------------------------------------------------------------------------
# Product overview
# ---------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Product profitability overview")
    sort_metric = st.radio(
        "Leaderboard ranking", ["Gross margin", "Gross profit", "Revenue"],
        horizontal=True, key="leaderboard_sort",
    )
    metric_map = {"Gross margin": "gross_margin_pct", "Gross profit": "gross_profit", "Revenue": "revenue"}
    sort_col = metric_map[sort_metric]
    leader = products.sort_values(sort_col, ascending=True)
    fig = px.bar(
        leader, x=sort_col, y="product_name", orientation="h", color="division",
        color_discrete_map=DIVISION_COLORS,
        hover_data={"gross_margin_pct": ":.2f", "gross_profit": ":$,.2f", "revenue": ":$,.2f",
                    "profit_per_unit": ":$.2f", "classification": True},
        labels={sort_col: sort_metric, "product_name": "Product", "division": "Division"},
        title=f"Product leaderboard — ranked by {sort_metric.lower()}",
    )
    if "margin" in sort_col:
        fig.add_vline(x=benchmark_pct, line_dash="dash", line_color=ROSE,
                      annotation_text=f"{benchmark_pct}% benchmark", annotation_position="top")
        fig.add_vline(x=portfolio_margin, line_dash="dot", line_color=NAVY,
                      annotation_text=f"Portfolio {portfolio_margin:.1f}%", annotation_position="bottom")
    show(fig, height=max(420, 35 * len(leader)))

    left, right = st.columns([1.05, 1])
    with left:
        st.markdown("#### Profit contribution structure")
        treemap = px.treemap(
            products, path=[px.Constant("Portfolio"), "division", "product_name"],
            values="gross_profit", color="gross_margin_pct", color_continuous_scale="RdYlGn",
            range_color=[0, 80], color_continuous_midpoint=benchmark_pct,
            hover_data={"revenue": ":$,.2f", "gross_profit": ":$,.2f", "gross_margin_pct": ":.1f",
                        "profit_share_pct": ":.2f"},
            title="Gross profit by division and product",
        )
        treemap.update_traces(textinfo="label+percent parent")
        show(treemap, height=480)
    with right:
        st.markdown("#### Monthly revenue and margin")
        if not monthly.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=monthly["month"], y=monthly["revenue"], name="Revenue",
                                 marker_color=TEAL, hovertemplate="$%{y:,.0f}<extra></extra>"), secondary_y=False)
            fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["gross_margin_pct"], name="Margin",
                                     mode="lines+markers", line=dict(color=ROSE, width=2),
                                     marker=dict(size=5),
                                     hovertemplate="%{y:.2f}%<extra></extra>"), secondary_y=True)
            lo = min(float(monthly["gross_margin_pct"].min()), portfolio_margin) - 3
            hi = max(float(monthly["gross_margin_pct"].max()), portfolio_margin) + 3
            fig.update_yaxes(title_text="Revenue (USD)", secondary_y=False)
            fig.update_yaxes(title_text="Gross margin (%)", range=[max(0, lo), min(100, hi)],
                             ticksuffix="%", secondary_y=True)
            fig.update_layout(title="Weighted margin is stable relative to revenue growth")
            show(fig, height=480)
        else:
            st.info("No monthly observations in this scope.")

    st.markdown("#### Full product KPI table")
    table(formatted_products(products), height=430)
    st.caption(
        "Margin volatility is the standard deviation of active-month weighted margins. It is near zero because "
        "unit prices and costs are effectively fixed in this dataset."
    )

# ---------------------------------------------------------------------------
# Divisions
# ---------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Division performance dashboard")
    if divisions.empty:
        st.info("No division data in this scope.")
    else:
        d = divisions.sort_values("revenue", ascending=False)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=d["division"], y=d["revenue"], name="Revenue", marker_color=TEAL,
                             hovertemplate="$%{y:,.0f}<extra></extra>"), secondary_y=False)
        fig.add_trace(go.Bar(x=d["division"], y=d["gross_profit"], name="Gross profit", marker_color=GREEN,
                             hovertemplate="$%{y:,.0f}<extra></extra>"), secondary_y=False)
        fig.add_trace(go.Scatter(x=d["division"], y=d["gross_margin_pct"], name="Weighted margin",
                                 mode="lines+markers", line=dict(color=ROSE, width=2.4),
                                 marker=dict(size=9), hovertemplate="%{y:.2f}%<extra></extra>"),
                      secondary_y=True)
        fig.update_yaxes(title_text="USD", secondary_y=False)
        fig.update_yaxes(title_text="Gross margin (%)", range=[0, 100], ticksuffix="%", secondary_y=True)
        fig.update_layout(title="Revenue vs profit conversion, with weighted margin", barmode="group")
        show(fig, 430)

        col1, col2 = st.columns([1, 1])
        with col1:
            box = px.box(
                scope, x="division", y="line_margin_pct", color="division",
                color_discrete_map=DIVISION_COLORS, points=False,
                labels={"division": "Division", "line_margin_pct": "Order-line margin (%)"},
                title="Distribution of order-line margins by division",
            )
            box.add_hline(y=benchmark_pct, line_dash="dash", line_color=ROSE,
                          annotation_text=f"{benchmark_pct}% benchmark", annotation_position="top left")
            show(box, 420)
        with col2:
            eff = px.bar(
                d, x="division", y="profit_revenue_index", color="division",
                color_discrete_map=DIVISION_COLORS,
                labels={"division": "Division", "profit_revenue_index": "Profit share ÷ revenue share"},
                title="Financial efficiency index (1.0 = proportional profit conversion)",
            )
            eff.add_hline(y=1, line_dash="dash", line_color=NAVY)
            show(eff, 420)

        division_table = divisions[[
            "division", "revenue", "gross_profit", "gross_margin_pct", "cost_ratio_pct",
            "revenue_share_pct", "profit_share_pct", "profit_revenue_index", "profit_per_unit",
            "line_margin_std_pp", "order_lines",
        ]].copy()
        for col, fn in {
            "revenue": lambda v: money(v, 2), "gross_profit": lambda v: money(v, 2),
            "gross_margin_pct": lambda v: pct(v, 2), "cost_ratio_pct": lambda v: pct(v, 2),
            "revenue_share_pct": lambda v: pct(v, 2), "profit_share_pct": lambda v: pct(v, 2),
            "profit_revenue_index": lambda v: num(v, 2), "profit_per_unit": lambda v: money(v, 2),
            "line_margin_std_pp": lambda v: num(v, 2) + " pp", "order_lines": lambda v: num(v, 0),
        }.items():
            division_table[col] = division_table[col].map(fn)
        division_table.columns = ["Division", "Revenue", "Gross profit", "Margin", "Cost ratio", "Rev. share",
                                  "Profit share", "P/R index", "Profit/unit", "Line-margin SD", "Order lines"]
        st.markdown("#### Division scorecard")
        table(division_table)
        strongest = divisions.loc[divisions["gross_margin_pct"].idxmax()]
        weakest = divisions.loc[divisions["gross_margin_pct"].idxmin()]
        st.info(
            f"Highest weighted margin: **{strongest['division']} ({pct(strongest['gross_margin_pct'],2)})**. "
            f"Lowest: **{weakest['division']} ({pct(weakest['gross_margin_pct'],2)})**. "
            "The box plot uses line-level margins; scorecard margins are revenue-weighted."
        )

# ---------------------------------------------------------------------------
# Cost and margin diagnostics
# ---------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Cost vs margin diagnostics")
    granularity = st.radio(
        "Scatter granularity", ["Product-month", "Order-line sample"], horizontal=True,
        key="scatter_granularity",
    )
    if granularity == "Product-month":
        scatter_df = (
            scope.groupby(["product_name", "division", "month"], as_index=False)
            .agg(sales=("sales", "sum"), cost=("cost", "sum"), units=("units", "sum"),
                 gross_profit=("gross_profit", "sum"))
        )
        scatter_df["margin"] = 100 * scatter_df["gross_profit"] / scatter_df["sales"]
        fig = px.scatter(
            scatter_df, x="sales", y="cost", size="units", color="margin",
            color_continuous_scale="RdYlGn", range_color=[0, 80], size_max=34,
            hover_name="product_name", hover_data={"division": True, "month": "|%b %Y", "units": ":,.0f"},
            labels={"sales": "Sales (USD)", "cost": "Cost (USD)", "margin": "Gross margin (%)"},
            title="Monthly product sales vs cost (bubble size = units)",
        )
        caption = "Product-month points above the 50% cost-ratio line are cost-heavy; points near the diagonal have near-zero margin."
    else:
        sample_n = min(len(scope), 3000)
        scatter_df = scope.sample(sample_n, random_state=42) if sample_n < len(scope) else scope.copy()
        fig = px.scatter(
            scatter_df, x="sales", y="cost", size="units", color="line_margin_pct",
            color_continuous_scale="RdYlGn", range_color=[0, 80], size_max=20,
            hover_name="product_name",
            hover_data={"division": True, "order_id": True, "units": True, "line_margin_pct": ":.2f"},
            labels={"sales": "Sales (USD)", "cost": "Cost (USD)", "line_margin_pct": "Gross margin (%)"},
            title=f"Order-line sales vs cost ({sample_n:,} lines)",
            render_mode="webgl",
        )
        caption = "Order-line view is sampled for responsiveness; color represents line-level gross margin."
    lim = float(max(scatter_df["sales"].max(), scatter_df["cost"].max()) * 1.04)
    line = np.linspace(0, lim, 80)
    fig.add_trace(go.Scatter(x=line, y=line, mode="lines", name="Cost = sales", line=dict(color=ROSE, dash="dash", width=1.4)))
    fig.add_trace(go.Scatter(x=line, y=0.5 * line, mode="lines", name="50% cost ratio", line=dict(color=GOLD, dash="dash", width=1.4)))
    fig.update_xaxes(range=[0, lim])
    fig.update_yaxes(range=[0, lim])
    show(fig, 500)
    st.caption(caption)

    col1, col2 = st.columns([1, 1])
    with col1:
        price_fig = px.scatter(
            products, x="avg_selling_price", y="gross_margin_pct", size="units", color="division",
            color_discrete_map=DIVISION_COLORS, size_max=42, hover_name="product_name",
            hover_data={"revenue": ":$,.0f", "profit_per_unit": ":$.2f", "cost_ratio_pct": ":.1f"},
            labels={"avg_selling_price": "Weighted average selling price (USD)",
                    "gross_margin_pct": "Gross margin (%)"},
            title="Price level does not guarantee margin efficiency",
        )
        price_fig.add_hline(y=benchmark_pct, line_dash="dash", line_color=ROSE,
                            annotation_text=f"{benchmark_pct}% benchmark", annotation_position="top left")
        show(price_fig, 420)
    with col2:
        quadrant = px.scatter(
            products, x="revenue_share_pct", y="gross_margin_pct", size="units", color="division",
            color_discrete_map=DIVISION_COLORS, size_max=42, hover_name="product_name",
            hover_data={"gross_profit": ":$,.0f", "cost_ratio_pct": ":.1f", "classification": True},
            labels={"revenue_share_pct": "Revenue share (%)", "gross_margin_pct": "Gross margin (%)"},
            title="Revenue materiality vs margin",
        )
        quadrant.add_vline(x=5, line_dash="dot", line_color=SLATE)
        quadrant.add_hline(y=benchmark_pct, line_dash="dash", line_color=ROSE)
        show(quadrant, 420)

    st.markdown("#### Margin risk register")
    if restrict:
        st.caption("Risk register uses the full date/division/search scope, even when charts are restricted to products above the benchmark.")
    show_flagged_only = st.checkbox("Show only products below benchmark or with High/Medium priority", value=True)
    risk_view = risks.copy()
    if show_flagged_only:
        risk_view = risk_view[
            (risk_view["gross_margin_pct"] < benchmark_pct) | (risk_view["risk_priority"].isin(["High", "Medium"]))
        ]
    risk_display = risk_view[[
        "product_name", "division", "factory", "gross_margin_pct", "cost_ratio_pct", "revenue_share_pct",
        "profit_share_pct", "cost_reduction_to_benchmark_pct", "risk_priority", "recommended_action", "risk_reason",
    ]].copy()
    for col, fn in {
        "gross_margin_pct": lambda v: pct(v, 1), "cost_ratio_pct": lambda v: pct(v, 1),
        "revenue_share_pct": lambda v: pct(v, 2), "profit_share_pct": lambda v: pct(v, 2),
        "cost_reduction_to_benchmark_pct": lambda v: pct(v, 1),
    }.items():
        risk_display[col] = risk_display[col].map(fn)
    risk_display.columns = ["Product", "Division", "Factory", "Margin", "Cost ratio", "Rev. share",
                            "Profit share", "Cost cut to benchmark", "Priority", "Recommended action", "Reason"]
    table(risk_display, height=360)
    st.caption(
        "Actions are decision hypotheses. Discontinuation review requires landed freight, returns, promotional, "
        "handling and contractual costs that are absent from this dataset."
    )

# ---------------------------------------------------------------------------
# Concentration
# ---------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Profit concentration and dependency")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: card("80% revenue", f"{conc.get('revenue_n80',0)}/{len(products)}", "products required", TEAL)
    with c2: card("80% profit", f"{conc.get('profit_n80',0)}/{len(products)}", "products required", GREEN)
    with c3: card("Top-3 profit", pct(conc.get("profit_top3_share_pct", 0), 1), "share of gross profit", GOLD)
    with c4: card("Profit HHI", num(conc.get("profit_hhi", 0), 0), "portfolio concentration", NAVY)
    with c5: card("Effective SKUs", num(conc.get("profit_effective_products", 0), 2), "by profit share", ROSE)

    col1, col2 = st.columns(2)
    with col1: show(pareto_figure(products, "revenue", "Revenue"), 480)
    with col2: show(pareto_figure(products, "gross_profit", "Gross profit"), 480)

    st.markdown("#### Dependency indicators")
    dep_cols = st.columns([1.25, 1])
    with dep_cols[0]:
        top5_profit = conc.get("profit_top5_share_pct", 0)
        st.progress(min(top5_profit / 100, 1.0), text=f"Top-5 profit share: {pct(top5_profit,2)}")
        top5_revenue = conc.get("revenue_top5_share_pct", 0)
        st.progress(min(top5_revenue / 100, 1.0), text=f"Top-5 revenue share: {pct(top5_revenue,2)}")
        st.markdown(
            f"**Read:** {conc.get('revenue_n80',0)} products ({pct(conc.get('revenue_pct_products_for_80',0),1)} "
            f"of the assortment) are needed to cross 80% of revenue; "
            f"{conc.get('profit_n80',0)} products are needed to cross 80% of profit. "
            f"By the fifth product, cumulative shares reach "
            f"{pct(conc.get('revenue_cumulative_at_n80_pct',0),1)} of revenue and "
            f"{pct(conc.get('profit_cumulative_at_n80_pct',0),1)} of profit."
        )
        st.caption("HHI and effective-SKU counts measure internal portfolio dependency, not market share or antitrust concentration.")
    with dep_cols[1]:
        top_states = states.head(10).sort_values("revenue", ascending=True)
        state_fig = px.bar(
            top_states, x="revenue_share_pct", y="state", orientation="h",
            color="gross_margin_pct", color_continuous_scale="Blues",
            hover_data={"order_lines": ":,.0f", "gross_profit": ":$,.0f"},
            labels={"revenue_share_pct": "Revenue share (%)", "state": "State / province",
                    "gross_margin_pct": "Margin (%)"},
            title="Top 10 states by revenue concentration",
        )
        show(state_fig, 380)
        st.caption(
            "High geographic volume is a capacity-planning signal—not proof of congestion. No freight-time, "
            "capacity, traffic or stockout variables are present."
        )

# ---------------------------------------------------------------------------
# Geography and factories
# ---------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Geographic and factory context")
    col1, col2 = st.columns([1.1, 1])
    with col1:
        region_fig = px.bar(
            regions, x="region", y=["revenue_share_pct", "profit_share_pct"], barmode="group",
            color_discrete_sequence=[TEAL, GREEN],
            labels={"region": "Region", "value": "Share (%)", "variable": "Measure"},
            title="Revenue and profit share by customer region",
        )
        show(region_fig, 400)
    with col2:
        margin_fig = px.bar(
            regions, x="region", y="gross_margin_pct", color="region",
            color_discrete_sequence=[NAVY, TEAL, GREEN, GOLD, ROSE],
            labels={"region": "Region", "gross_margin_pct": "Weighted margin (%)"},
            title="Weighted margin by customer region",
        )
        margin_fig.update_yaxes(range=[0, 100], ticksuffix="%")
        show(margin_fig, 400)
    st.caption(
        f"Regional margin spread in the current scope is "
        f"{num(regions['gross_margin_pct'].max() - regions['gross_margin_pct'].min(),2)} pp. "
        "Product mix, not geography, explains most margin variation."
    )

    st.markdown("#### State / province scorecard")
    state_display = states.head(15)[[
        "state", "revenue", "gross_profit", "gross_margin_pct", "revenue_share_pct",
        "profit_share_pct", "order_lines", "order_line_share_pct",
    ]].copy()
    for col, fn in {
        "revenue": lambda v: money(v, 2), "gross_profit": lambda v: money(v, 2),
        "gross_margin_pct": lambda v: pct(v, 2), "revenue_share_pct": lambda v: pct(v, 2),
        "profit_share_pct": lambda v: pct(v, 2), "order_lines": lambda v: num(v, 0),
        "order_line_share_pct": lambda v: pct(v, 2),
    }.items():
        state_display[col] = state_display[col].map(fn)
    state_display.columns = ["State / province", "Revenue", "Gross profit", "Margin", "Rev. share",
                             "Profit share", "Order lines", "Line share"]
    table(state_display, height=390)

    st.markdown("#### Factory economics and supplied coordinates")
    fac = factories.dropna(subset=["latitude", "longitude"]).copy()
    if not fac.empty:
        factory_map = px.scatter_geo(
            fac, lat="latitude", lon="longitude", size="revenue", color="gross_margin_pct",
            color_continuous_scale="RdYlGn", range_color=[0, 80], size_max=42,
            hover_name="factory", projection="albers usa", scope="usa",
            hover_data={"products": True, "revenue": ":$,.0f", "gross_profit": ":$,.0f",
                        "gross_margin_pct": ":.2f", "revenue_share_pct": ":.2f"},
            labels={"gross_margin_pct": "Margin (%)", "revenue": "Revenue"},
            title="Factory footprint (bubble = attributed revenue; color = margin)",
        )
        factory_map.update_layout(
            geo=dict(
                bgcolor="rgba(0,0,0,0)", landcolor="#E7EEF1", subunitcolor="white",
                showlakes=False, showland=True, showcoastlines=False,
            )
        )
        show(factory_map, 500)
    factory_table = factories[[
        "factory", "products", "revenue", "gross_profit", "gross_margin_pct", "cost_ratio_pct",
        "revenue_share_pct", "profit_share_pct", "latitude", "longitude",
    ]].copy()
    for col, fn in {
        "revenue": lambda v: money(v, 2), "gross_profit": lambda v: money(v, 2),
        "gross_margin_pct": lambda v: pct(v, 2), "cost_ratio_pct": lambda v: pct(v, 2),
        "revenue_share_pct": lambda v: pct(v, 2), "profit_share_pct": lambda v: pct(v, 2),
        "latitude": lambda v: num(v, 4), "longitude": lambda v: num(v, 4),
    }.items():
        factory_table[col] = factory_table[col].map(fn)
    factory_table.columns = ["Factory", "Products", "Revenue", "Gross profit", "Margin", "Cost ratio",
                             "Rev. share", "Profit share", "Latitude", "Longitude"]
    table(factory_table)
    with st.expander("Product-to-factory correlation from the project brief"):
        mapping = pd.DataFrame(
            [{"product_name": product, "division": products_all.loc[products_all["product_name"] == product, "division"].iloc[0]
              if (products_all["product_name"] == product).any() else "—", "factory": factory}
             for product, factory in PRODUCT_FACTORY.items()]
        )
        table(mapping, height=420)

    st.warning(
        "**Data integrity:** the project brief's conclusion mentions shipping-route efficiency, but the supplied "
        f"ship dates are {report['ship_days_min']:.0f}–{report['ship_days_max']:.0f} days after order dates "
        f"(median {report['ship_days_median']:.0f}). All {report['order_id_year_mismatch_rows']:,} Order ID "
        "years conflict with Order Date years. No delay, congestion or route-efficiency KPI is reported here. "
        "Factory coordinates and links are reference data, not verified shipment routes."
    )

# ---------------------------------------------------------------------------
# Executive brief
# ---------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Executive brief for stakeholders")
    st.markdown(
        f"""
        <div style="background:white;border-left:5px solid {TEAL};border-radius:10px;padding:16px 18px;margin-bottom:12px;">
          <b>Bottom line.</b> In the current scope, {money(k['revenue'],2)} of revenue generates
          {money(k['gross_profit'],2)} of gross profit ({pct(portfolio_margin,2)} weighted margin).
          The top five products contribute {pct(k.get('top5_profit_share_pct',0),1)} of profit.
          Margin risk is concentrated in a small cost-heavy tail rather than in customer geography or short-term volatility.
        </div>
        """,
        unsafe_allow_html=True,
    )
    findings = st.columns(2)
    with findings[0]:
        st.markdown("#### Findings")
        st.markdown(
            f"- **Scale ≠ profitability:** high-revenue lines can still fall below the {benchmark_pct}% benchmark.\n"
            f"- **Division gap:** {len(divisions)} divisions show a "
            f"{num(divisions['gross_margin_pct'].max() - divisions['gross_margin_pct'].min(),1)} pp weighted-margin spread.\n"
            f"- **Concentration:** {conc.get('profit_n80',0)} of {len(products)} products are needed to cross 80% of profit.\n"
            f"- **Stability:** monthly margin volatility is low in the full dataset; structural economics dominate."
        )
    with findings[1]:
        st.markdown("#### Decisions")
        st.markdown(
            "- Protect continuity and margin on the core profit engines.\n"
            "- Run controlled repricing / supplier-cost tests for material low-margin SKUs.\n"
            "- Require cost teardown or discontinuation review for severe outliers.\n"
            "- Diversify with measured pilots, and correct source-system dates before logistics claims."
        )
    st.markdown("#### Public-sector interpretation")
    st.info(
        "Use these results for supply-chain resilience, supplier diversification and data-quality assurance. "
        "They do not establish market power, consumer harm, regulatory compliance or delivery reliability. "
        "Portfolio HHI is an internal dependency measure; the shipment dates are not suitable for route analysis."
    )
    st.markdown("#### Download written deliverables")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        download_button("Research paper (DOCX)", ROOT / "Research_Paper_Nassau_Candy_Profitability.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "rp_docx")
    with d2:
        download_button("Research paper (MD)", ROOT / "Research_Paper_Nassau_Candy_Profitability.md",
                        "text/markdown", "rp_md")
    with d3:
        download_button("Executive summary (DOCX)", ROOT / "Executive_Summary_Government_Stakeholders.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "es_docx")
    with d4:
        download_button("Executive summary (MD)", ROOT / "Executive_Summary_Government_Stakeholders.md",
                        "text/markdown", "es_md")

# ---------------------------------------------------------------------------
# Methods and data
# ---------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Methods, definitions and data quality")
    method_cols = st.columns([1.0, 1.0])
    with method_cols[0]:
        st.markdown("#### KPI definitions")
        definitions = pd.DataFrame([
            ["Gross margin (%)", "Σ Gross Profit ÷ Σ Sales × 100"],
            ["Profit per unit", "Σ Gross Profit ÷ Σ Units"],
            ["Revenue contribution", "Product sales ÷ total sales × 100"],
            ["Profit contribution", "Product profit ÷ total profit × 100"],
            ["Cost ratio", "Σ Cost ÷ Σ Sales × 100"],
            ["Margin volatility", "SD of active monthly weighted margins, in pp"],
            ["Profit–revenue index", "Profit share ÷ revenue share"],
            ["Pareto", "Fewest ranked products to cross 80%"],
            ["HHI / effective SKUs", "10,000 × Σ share² / 10,000 ÷ HHI"],
        ], columns=["Metric", "Formula / meaning"])
        table(definitions, height=330)
        st.markdown("#### Classification rules")
        st.markdown(
            f"- High sales: ≥ 5% of revenue in current scope\n"
            f"- Low margin: below {benchmark_pct}% benchmark\n"
            "- Low sales: < 1% of revenue; low profit: < 0.5% of profit\n"
            "- High profit: ≥ 10% of profit; cost-heavy: ≥ 50% cost ratio"
        )
    with method_cols[1]:
        st.markdown("#### Source-system validation")
        quality_rows = pd.DataFrame(
            [{"Check": str(key), "Result": json.dumps(value) if isinstance(value, (dict, list)) else str(value)}
             for key, value in report.items()]
        )
        table(quality_rows, height=470)
        st.caption("Validation report for the complete source dataset, independent of dashboard filters.")

    st.markdown("#### Limitations")
    st.markdown(
        "Gross profit excludes freight, warehousing, discounts, returns, promotions, overhead, taxes and capital "
        "costs. No price elasticity, competitor prices, market size, channel margin or product lifecycle data are "
        "available. Ten SKUs have very few order lines. Factory coordinates and links are supplied reference data. "
        "The route-efficiency wording in the template conclusion is not supported by the implausible ship dates."
    )
    st.markdown("#### Data preview and downloads")
    preview = scope.head(200)[[
        "order_date", "order_id", "product_name", "division", "sales", "units", "cost",
        "gross_profit", "line_margin_pct", "region", "state", "factory",
    ]].copy()
    preview["order_date"] = preview["order_date"].dt.strftime("%Y-%m-%d")
    preview["line_margin_pct"] = preview["line_margin_pct"].map(lambda v: pct(v, 2))
    for col in ["sales", "cost", "gross_profit"]:
        preview[col] = preview[col].map(lambda v: money(v, 2))
    preview.columns = ["Order date", "Order ID", "Product", "Division", "Sales", "Units", "Cost",
                       "Gross profit", "Margin", "Region", "State", "Factory"]
    table(preview, height=360)
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button("Filtered lines (CSV)", scope.to_csv(index=False).encode("utf-8"),
                           "nassau_filtered_order_lines.csv", "text/csv", width="stretch", key="methods_lines")
    with d2:
        download_button("Full clean dataset (CSV)", CLEAN_DATA_PATH, "text/csv", "methods_clean")
    with d3:
        download_button("Analysis workbook (XLSX)", OUTPUT_DIR / "Nassau_Profitability_Analysis.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "methods_xlsx")
