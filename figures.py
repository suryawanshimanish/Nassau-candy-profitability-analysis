"""Static, publication-quality figures for the research paper."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from analytics import DIVISION_COLORS, PALETTE

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelweight": "bold",
    "axes.edgecolor": "#B8C4CE",
    "axes.grid": True,
    "grid.alpha": 0.20,
    "grid.color": "#8AA0AD",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

USD = FuncFormatter(lambda x, _: f"${x:,.0f}")
PCT = FuncFormatter(lambda x, _: f"{x:.0f}%")


def _save(fig: plt.Figure, path: Path) -> Path:
    fig.savefig(path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _short(name: str) -> str:
    replacements = {
        "Wonka Bar - ": "", "Lickable Wallpaper": "Lickable Wallpaper",
        "Everlasting Gobstopper": "Everlasting Gobstopper",
        "Fizzy Lifting Drinks": "Fizzy Lifting Drinks",
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name


def _division_bar_colors(products: pd.DataFrame) -> list[str]:
    return [DIVISION_COLORS.get(d, PALETTE["slate"]) for d in products["division"]]


def all_figures(
    df: pd.DataFrame,
    products: pd.DataFrame,
    divisions: pd.DataFrame,
    regions: pd.DataFrame,
    states: pd.DataFrame,
    factories: pd.DataFrame,
    monthly: pd.DataFrame,
    out_dir: str | Path,
) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    portfolio_margin = 100 * df["gross_profit"].sum() / df["sales"].sum()

    # 1. Division revenue, profit and weighted margin.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.35, 1]})
    d = divisions.sort_values("revenue", ascending=False)
    x = np.arange(len(d))
    axes[0].bar(x - 0.18, d["revenue"], 0.36, label="Revenue", color=PALETTE["teal"])
    axes[0].bar(x + 0.18, d["gross_profit"], 0.36, label="Gross profit", color=PALETTE["green"])
    axes[0].set_xticks(x, d["division"])
    axes[0].set_ylabel("USD")
    axes[0].yaxis.set_major_formatter(USD)
    axes[0].set_title("Revenue and gross profit by division")
    axes[0].legend(frameon=False)
    for i, (rev, prof) in enumerate(zip(d["revenue"], d["gross_profit"])):
        axes[0].text(i - 0.18, rev, f"${rev/1000:.1f}k", ha="center", va="bottom", fontsize=7.5)
        axes[0].text(i + 0.18, prof, f"${prof/1000:.1f}k", ha="center", va="bottom", fontsize=7.5)
    colors = [DIVISION_COLORS.get(v, PALETTE["slate"]) for v in d["division"]]
    axes[1].bar(d["division"], d["gross_margin_pct"], color=colors, width=0.58)
    axes[1].axhline(portfolio_margin, color=PALETTE["navy"], linestyle="--", linewidth=1.2,
                    label=f"Portfolio {portfolio_margin:.1f}%")
    axes[1].set_ylim(0, 80)
    axes[1].yaxis.set_major_formatter(PCT)
    axes[1].set_title("Weighted gross margin")
    axes[1].legend(frameon=False, loc="upper right")
    for i, v in enumerate(d["gross_margin_pct"]):
        axes[1].text(i, v + 1.2, f"{v:.1f}%", ha="center", fontsize=8)
    fig.suptitle("Division performance: Chocolate carries both scale and margin", fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    paths["division"] = _save(fig, out / "01_division_performance.png")

    # 2. Product margin leaderboard.
    p = products.sort_values("gross_margin_pct")
    fig, ax = plt.subplots(figsize=(10.5, 7.2))
    ax.barh(p["product_name"], p["gross_margin_pct"], color=_division_bar_colors(p), height=0.72)
    ax.axvline(60, color=PALETTE["rose"], ls="--", lw=1.3, label="60% risk benchmark")
    ax.axvline(portfolio_margin, color=PALETTE["navy"], ls=":", lw=1.3, label=f"Portfolio {portfolio_margin:.1f}%")
    ax.set_xlim(0, 88)
    ax.xaxis.set_major_formatter(PCT)
    ax.set_xlabel("Aggregate gross margin")
    ax.set_title("Product-level margin leaderboard")
    for i, v in enumerate(p["gross_margin_pct"]):
        ax.text(v + 0.8, i, f"{v:.1f}%", va="center", fontsize=7.8)
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=DIVISION_COLORS["Chocolate"]),
        plt.Rectangle((0, 0), 1, 1, color=DIVISION_COLORS["Other"]),
        plt.Rectangle((0, 0), 1, 1, color=DIVISION_COLORS["Sugar"]),
    ]
    ax.legend(handles + ax.get_legend_handles_labels()[0], ["Chocolate", "Other", "Sugar", "60% benchmark", "Portfolio margin"],
              loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout()
    paths["margin"] = _save(fig, out / "02_product_margin_leaderboard.png")

    # 3. Profit contribution.
    top = products.sort_values("gross_profit", ascending=False).head(10).sort_values("gross_profit")
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    ax.barh(top["product_name"], top["gross_profit"], color=_division_bar_colors(top), height=0.72)
    ax.xaxis.set_major_formatter(USD)
    ax.set_xlabel("Gross profit (USD)")
    ax.set_title("Top 10 products by gross profit contribution")
    for i, (v, share) in enumerate(zip(top["gross_profit"], top["profit_share_pct"])):
        ax.text(v + 250, i, f"${v/1000:.1f}k  ({share:.1f}%)", va="center", fontsize=7.6)
    ax.set_xlim(0, top["gross_profit"].max() * 1.24)
    fig.tight_layout()
    paths["profit"] = _save(fig, out / "03_profit_contribution.png")

    # 4. Cost-versus-sales diagnostics by product-month.
    pm = (
        df.groupby(["product_name", "division", "month"], as_index=False)
        .agg(sales=("sales", "sum"), cost=("cost", "sum"), units=("units", "sum"), gross_profit=("gross_profit", "sum"))
    )
    pm["margin"] = 100 * pm["gross_profit"] / pm["sales"]
    fig, ax = plt.subplots(figsize=(9.2, 6.3))
    sc = ax.scatter(pm["sales"], pm["cost"], s=np.sqrt(pm["units"]) * 9, c=pm["margin"],
                    cmap="RdYlGn", vmin=0, vmax=80, alpha=0.78, edgecolor="white", linewidth=0.45)
    lim = max(pm["sales"].max(), pm["cost"].max()) * 1.05
    line = np.linspace(0, lim, 100)
    ax.plot(line, line, color=PALETTE["rose"], ls="--", lw=1.2, label="Cost = sales (zero margin)")
    ax.plot(line, 0.5 * line, color=PALETTE["gold"], ls="--", lw=1.2, label="50% cost ratio")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.xaxis.set_major_formatter(USD)
    ax.yaxis.set_major_formatter(USD)
    ax.set_xlabel("Monthly sales")
    ax.set_ylabel("Monthly cost")
    ax.set_title("Cost–sales diagnostics: points near the diagonal are cost-heavy")
    for name in ["Kazookles", "Lickable Wallpaper"]:
        row = pm[pm["product_name"] == name]
        if not row.empty:
            r = row.loc[row["sales"].idxmax()]
            ax.annotate(name, (r["sales"], r["cost"]), xytext=(8, 8), textcoords="offset points",
                        fontsize=8, color=PALETTE["navy"], arrowprops={"arrowstyle": "-", "color": PALETTE["navy"], "lw": 0.8})
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("Gross margin (%)")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    paths["cost_scatter"] = _save(fig, out / "04_cost_sales_scatter.png")

    # 5. Revenue/profit margin-risk quadrant.
    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    ax.scatter(products["revenue"], products["gross_margin_pct"],
               s=np.sqrt(products["units"]) * 4.5, c=_division_bar_colors(products),
               alpha=0.80, edgecolor="white", linewidth=0.8)
    ax.axvline(0.05 * df["sales"].sum(), color=PALETTE["slate"], ls=":", lw=1.2)
    ax.axhline(60, color=PALETTE["rose"], ls="--", lw=1.2)
    ax.set_xscale("symlog", linthresh=200)
    ax.xaxis.set_major_formatter(USD)
    ax.yaxis.set_major_formatter(PCT)
    ax.set_xlabel("Revenue (symlog scale; vertical rule = 5% of portfolio)")
    ax.set_ylabel("Gross margin")
    ax.set_title("Margin-risk quadrant: material revenue versus margin")
    for name in ["Kazookles", "Lickable Wallpaper", "Wonka Bar - Nutty Crunch Surprise", "Everlasting Gobstopper"]:
        r = products[products["product_name"] == name]
        if not r.empty:
            r = r.iloc[0]
            ax.annotate(_short(name), (r["revenue"], r["gross_margin_pct"]), xytext=(6, 6),
                        textcoords="offset points", fontsize=7.5, color=PALETTE["navy"])
    fig.tight_layout()
    paths["quadrant"] = _save(fig, out / "05_margin_risk_quadrant.png")

    # 6. Pareto concentration.
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.7))
    for ax, (metric, label) in zip(axes, [("revenue", "Revenue"), ("gross_profit", "Gross profit")]):
        q = products.sort_values(metric, ascending=False).reset_index(drop=True)
        cumulative = 100 * q[metric].cumsum() / q[metric].sum()
        ax.bar(np.arange(len(q)), q[metric], color=_division_bar_colors(q), width=0.72)
        ax.set_xticks(np.arange(len(q)))
        ax.set_xticklabels([_short(n) for n in q["product_name"]], rotation=58, ha="right", fontsize=7)
        ax.set_ylabel("USD")
        ax.yaxis.set_major_formatter(USD)
        ax.set_title(f"{label} Pareto")
        ax2 = ax.twinx()
        ax2.plot(np.arange(len(q)), cumulative, color=PALETTE["navy"], marker="o", ms=3.5, lw=1.7)
        ax2.axhline(80, color=PALETTE["rose"], ls="--", lw=1.2)
        ax2.set_ylim(0, 105)
        ax2.set_ylabel("Cumulative share (%)")
        ax2.yaxis.set_major_formatter(PCT)
        ax2.grid(False)
        n80 = int(np.searchsorted((cumulative / 100).to_numpy(), 0.8) + 1)
        ax2.annotate(f"{n80}/{len(q)} products cross 80%", xy=(n80 - 1, 80), xytext=(0.32, 0.72),
                     textcoords="axes fraction", fontsize=8, color=PALETTE["rose"],
                     arrowprops={"arrowstyle": "->", "color": PALETTE["rose"], "lw": 0.9})
    fig.suptitle("Profit is more concentrated than revenue", fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    paths["pareto"] = _save(fig, out / "06_pareto_concentration.png")

    # 7. Monthly revenue and margin trend.
    fig, ax = plt.subplots(figsize=(11.5, 4.6))
    ax.bar(monthly["month"], monthly["revenue"], color=PALETTE["teal"], alpha=0.82, width=20, label="Revenue")
    ax.set_ylabel("Revenue (USD)")
    ax.yaxis.set_major_formatter(USD)
    ax2 = ax.twinx()
    ax2.plot(monthly["month"], monthly["gross_margin_pct"], color=PALETTE["rose"], marker="o", ms=3.5, lw=1.6, label="Margin")
    ax2.axhline(portfolio_margin, color=PALETTE["navy"], ls="--", lw=1.0)
    ax2.set_ylim(60, 70)
    ax2.set_ylabel("Gross margin (%)")
    ax2.yaxis.set_major_formatter(PCT)
    ax2.grid(False)
    ax.set_title("Monthly revenue grows; weighted margin stays within a narrow band")
    ax.legend(loc="upper left", frameon=False)
    ax2.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    paths["trend"] = _save(fig, out / "07_monthly_trend.png")

    # 8. Geographic volume concentration.
    top_states = states.sort_values("revenue", ascending=False).head(10)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw={"width_ratios": [1.5, 1]})
    axes[0].barh(top_states["state"][::-1], top_states["revenue_share_pct"][::-1], color=PALETTE["teal"])
    axes[0].xaxis.set_major_formatter(PCT)
    axes[0].set_xlabel("Share of portfolio revenue")
    axes[0].set_title("Top 10 states/provinces by revenue")
    for i, v in enumerate(top_states["revenue_share_pct"][::-1]):
        axes[0].text(v + 0.2, i, f"{v:.1f}%", va="center", fontsize=7.5)
    r = regions.sort_values("revenue", ascending=False)
    axes[1].bar(r["region"], r["revenue_share_pct"], color=PALETTE["gold"], width=0.6)
    axes[1].yaxis.set_major_formatter(PCT)
    axes[1].set_title("Revenue share by region")
    for i, (share, margin) in enumerate(zip(r["revenue_share_pct"], r["gross_margin_pct"])):
        axes[1].text(i, share + 0.6, f"{share:.1f}%\n({margin:.1f}% GM)", ha="center", fontsize=7.2)
    axes[1].set_ylim(0, max(r["revenue_share_pct"]) * 1.28)
    fig.tight_layout()
    paths["geography"] = _save(fig, out / "08_geographic_concentration.png")

    # 9. Factory coordinate plot.
    f = factories.sort_values("revenue", ascending=False)
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    sizes = 80 + 900 * f["revenue"] / f["revenue"].max()
    sc = ax.scatter(f["longitude"], f["latitude"], s=sizes, c=f["gross_margin_pct"],
                    cmap="RdYlGn", vmin=0, vmax=75, alpha=0.88, edgecolor=PALETTE["navy"], linewidth=1.0)
    for row in f.itertuples(index=False):
        label = f"{row.factory}\n{row.revenue_share_pct:.1f}% rev | {row.gross_margin_pct:.1f}% GM"
        ax.annotate(label, (row.longitude, row.latitude), xytext=(8, 7), textcoords="offset points",
                    fontsize=7.4, color=PALETTE["navy"])
    ax.set_xlim(-118, -76)
    ax.set_ylim(28, 53)
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    ax.set_title("Factory coordinates from the project brief (bubble = revenue; color = margin)")
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("Gross margin (%)")
    fig.tight_layout()
    paths["factory"] = _save(fig, out / "09_factory_coordinates.png")

    return paths
