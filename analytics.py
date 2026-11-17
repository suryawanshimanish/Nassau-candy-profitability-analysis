"""Shared data preparation and profitability analytics for the Nassau Candy project."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
RAW_DATA_CANDIDATES = [
    DATA_DIR / "Nassau Candy Distributor.csv",
    Path("/home/user/uploads/Nassau Candy Distributor.csv"),
]
CLEAN_DATA_PATH = DATA_DIR / "nassau_candy_clean.csv"

COLUMN_MAP = {
    "Row ID": "row_id",
    "Order ID": "order_id",
    "Order Date": "order_date_raw",
    "Ship Date": "ship_date_raw",
    "Ship Mode": "ship_mode",
    "Customer ID": "customer_id",
    "Country/Region": "country",
    "City": "city",
    "State/Province": "state",
    "Postal Code": "postal_code",
    "Division": "division",
    "Region": "region",
    "Product ID": "product_id",
    "Product Name": "source_product_name",
    "Sales": "sales",
    "Units": "units",
    "Gross Profit": "gross_profit",
    "Cost": "cost",
}

PRODUCT_NAME_FIXES = {
    "Wonka Bar -Scrumdiddlyumptious": "Wonka Bar - Scrumdiddlyumptious",
}

FACTORY_COORDS = pd.DataFrame(
    [
        {"factory": "Lot's O' Nuts", "latitude": 32.881893, "longitude": -111.768036},
        {"factory": "Wicked Choccy's", "latitude": 32.076176, "longitude": -81.088371},
        {"factory": "Sugar Shack", "latitude": 48.119140, "longitude": -96.181150},
        {"factory": "Secret Factory", "latitude": 41.446333, "longitude": -90.565487},
        {"factory": "The Other Factory", "latitude": 35.117500, "longitude": -89.971107},
    ]
)

PRODUCT_FACTORY = {
    "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
    "Wonka Bar - Scrumdiddlyumptious": "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's",
    "Laffy Taffy": "Sugar Shack",
    "SweeTARTS": "Sugar Shack",
    "Nerds": "Sugar Shack",
    "Fun Dip": "Sugar Shack",
    "Fizzy Lifting Drinks": "Sugar Shack",
    "Everlasting Gobstopper": "Secret Factory",
    "Hair Toffee": "The Other Factory",
    "Lickable Wallpaper": "Secret Factory",
    "Wonka Gum": "Secret Factory",
    "Kazookles": "The Other Factory",
}

DIVISION_COLORS = {
    "Chocolate": "#2D6A4F",
    "Sugar": "#E9A23B",
    "Other": "#B54771",
}
PALETTE = {
    "navy": "#14213D",
    "teal": "#168AAD",
    "green": "#2D6A4F",
    "gold": "#E9A23B",
    "rose": "#B54771",
    "slate": "#5B6573",
    "light": "#EEF4F6",
}

NUMERIC_COLUMNS = ["sales", "cost", "gross_profit", "units"]
TEXT_COLUMNS = [
    "order_id", "ship_mode", "country", "city", "state", "postal_code",
    "division", "region", "product_id", "source_product_name",
]


def _as_python(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def _json_safe(obj: dict[str, Any]) -> dict[str, Any]:
    def convert(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): convert(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [convert(v) for v in value]
        return _as_python(value)
    return {str(k): convert(v) for k, v in obj.items()}


def load_and_clean(source: str | Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load, validate and enrich the source order-line file.

    Zero-sales rows, missing/nonpositive units, and profit records that do not
    reconcile to Sales - Cost are handled explicitly. Negative gross profit is
    treated as a valid economic outcome, not as an invalid record.
    """
    path = Path(source) if source else next((p for p in RAW_DATA_CANDIDATES if p.exists()), None)
    if path is None:
        raise FileNotFoundError("Could not locate the Nassau Candy source CSV.")

    raw = pd.read_csv(path, dtype={"Postal Code": "string"})
    report: dict[str, Any] = {
        "source_file": str(path),
        "source_rows": int(len(raw)),
        "source_columns": int(raw.shape[1]),
        "exact_duplicate_rows": int(raw.duplicated().sum()),
        "duplicate_row_ids": int(raw["Row ID"].duplicated().sum()),
        "missing_values_by_column": {k: int(v) for k, v in raw.isna().sum().items()},
    }

    df = raw.rename(columns=COLUMN_MAP).copy()
    for col in TEXT_COLUMNS:
        df[col] = df[col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)

    # Standardize the one malformed product label while keeping the source label for audit.
    df["product_name"] = df["source_product_name"].replace(PRODUCT_NAME_FIXES)
    report["standardized_product_labels"] = {
        "Wonka Bar -Scrumdiddlyumptious": "Wonka Bar - Scrumdiddlyumptious"
    }

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Unit imputation rule: product median, then global median; never zero.
    invalid_units = df["units"].isna() | (df["units"] <= 0)
    report["missing_or_invalid_units"] = int(invalid_units.sum())
    product_medians = df.groupby("product_name")["units"].median()
    global_median = df["units"].median()
    replacement = df["product_name"].map(product_medians).fillna(global_median)
    df.loc[invalid_units, "units"] = replacement.loc[invalid_units]
    df["units"] = df["units"].fillna(1).round().clip(lower=1).astype(int)
    report["units_imputed"] = int(invalid_units.sum())

    zero_or_negative_sales = df["sales"].isna() | (df["sales"] <= 0)
    invalid_cost = df["cost"].isna() | (df["cost"] < 0)
    identity_gap = (df["gross_profit"] - (df["sales"] - df["cost"])).abs()
    invalid_profit = df["gross_profit"].isna() | (identity_gap > 0.011)
    drop_mask = zero_or_negative_sales | invalid_cost | invalid_profit
    report["zero_or_invalid_sales_rows"] = int(zero_or_negative_sales.sum())
    report["invalid_cost_rows"] = int(invalid_cost.sum())
    report["invalid_profit_identity_rows"] = int(invalid_profit.sum())
    report["max_profit_identity_gap"] = float(np.nanmax(identity_gap.to_numpy()))
    report["rows_removed_for_validation"] = int(drop_mask.sum())
    df = df.loc[~drop_mask].copy()
    df["gross_profit"] = df["sales"] - df["cost"]

    # Dates are DD-MM-YYYY in the supplied file.
    for raw_col, out_col in [("order_date_raw", "order_date"), ("ship_date_raw", "ship_date")]:
        parsed = pd.to_datetime(df[raw_col], format="%d-%m-%Y", errors="coerce")
        fallback = pd.to_datetime(df.loc[parsed.isna(), raw_col], dayfirst=True, errors="coerce")
        parsed.loc[fallback.index] = fallback
        df[out_col] = parsed
    report["unparseable_order_dates"] = int(df["order_date"].isna().sum())
    report["unparseable_ship_dates"] = int(df["ship_date"].isna().sum())
    df = df.dropna(subset=["order_date"]).copy()

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["row_id"], keep="first").copy()
    report["duplicate_row_ids_removed"] = int(before_dedup - len(df))

    # Line-level unit economics.
    df["sales_per_unit"] = df["sales"] / df["units"]
    df["cost_per_unit"] = df["cost"] / df["units"]
    df["profit_per_unit"] = df["gross_profit"] / df["units"]
    df["line_margin_pct"] = 100 * df["gross_profit"] / df["sales"]
    df["month"] = df["order_date"].dt.to_period("M").dt.to_timestamp()
    df["ship_days"] = (df["ship_date"] - df["order_date"]).dt.days
    df["factory"] = df["product_name"].map(PRODUCT_FACTORY)
    df["division"] = df["division"].replace({"Chocolate": "Chocolate", "Sugar": "Sugar", "Other": "Other"})
    report["unmapped_factory_products"] = int(df["factory"].isna().sum())

    order_id_year = pd.to_numeric(df["order_id"].str.extract(r"^[A-Z]{2}-(\d{4})-", expand=False), errors="coerce")
    report["order_id_year_mismatch_rows"] = int((order_id_year != df["order_date"].dt.year).sum())
    report["order_date_min"] = df["order_date"].min()
    report["order_date_max"] = df["order_date"].max()
    report["ship_date_min"] = df["ship_date"].min()
    report["ship_date_max"] = df["ship_date"].max()
    report["ship_days_min"] = float(df["ship_days"].min())
    report["ship_days_median"] = float(df["ship_days"].median())
    report["ship_days_max"] = float(df["ship_days"].max())
    report["negative_ship_days"] = int((df["ship_days"] < 0).sum())
    report["clean_rows"] = int(len(df))
    report["unique_orders"] = int(df["order_id"].nunique())
    report["unique_products"] = int(df["product_name"].nunique())
    report["unique_divisions"] = int(df["division"].nunique())
    report["countries"] = {str(k): int(v) for k, v in df["country"].value_counts().to_dict().items()}

    ordered_cols = [
        "row_id", "order_id", "order_date", "ship_date", "ship_mode", "customer_id",
        "country", "city", "state", "postal_code", "division", "region", "product_id",
        "product_name", "source_product_name", "factory", "sales", "units", "gross_profit",
        "cost", "sales_per_unit", "cost_per_unit", "profit_per_unit", "line_margin_pct",
        "month", "ship_days",
    ]
    df = df[ordered_cols].sort_values("order_date").reset_index(drop=True)
    return df, _json_safe(report)


def summarize(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Aggregate monetary and efficiency metrics for any grouping."""
    if df.empty:
        return pd.DataFrame(columns=group_cols)
    total_revenue = df["sales"].sum()
    total_profit = df["gross_profit"].sum()
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            revenue=("sales", "sum"),
            gross_profit=("gross_profit", "sum"),
            cost=("cost", "sum"),
            units=("units", "sum"),
            order_lines=("row_id", "size"),
            orders=("order_id", "nunique"),
            products=("product_name", "nunique"),
        )
        .reset_index()
    )
    grouped["gross_margin_pct"] = 100 * grouped["gross_profit"] / grouped["revenue"]
    grouped["cost_ratio_pct"] = 100 * grouped["cost"] / grouped["revenue"]
    grouped["profit_per_unit"] = grouped["gross_profit"] / grouped["units"]
    grouped["avg_selling_price"] = grouped["revenue"] / grouped["units"]
    grouped["revenue_share_pct"] = 100 * grouped["revenue"] / total_revenue
    grouped["profit_share_pct"] = 100 * grouped["gross_profit"] / total_profit
    grouped["profit_revenue_index"] = grouped["profit_share_pct"] / grouped["revenue_share_pct"]
    return grouped


def monthly_metrics(df: pd.DataFrame, group_cols: list[str] | None = None) -> pd.DataFrame:
    """Monthly weighted margin; volatility is measured only over active months."""
    cols = ["month"] + (group_cols or [])
    if df.empty:
        return pd.DataFrame(columns=cols + ["revenue", "gross_profit", "gross_margin_pct"])
    grouped = (
        df.groupby(cols, dropna=False)
        .agg(revenue=("sales", "sum"), gross_profit=("gross_profit", "sum"),
             cost=("cost", "sum"), units=("units", "sum"), order_lines=("row_id", "size"))
        .reset_index()
    )
    grouped["gross_margin_pct"] = 100 * grouped["gross_profit"] / grouped["revenue"]
    return grouped


def product_metrics(df: pd.DataFrame, margin_benchmark: float = 0.60) -> pd.DataFrame:
    """Product leaderboard, classifications, volatility, and decision flags."""
    products = summarize(df, ["product_name", "division", "product_id", "factory"])
    if products.empty:
        return products
    total_revenue = df["sales"].sum()
    total_profit = df["gross_profit"].sum()
    portfolio_margin = 100 * total_profit / total_revenue
    benchmark_pct = 100 * margin_benchmark

    monthly = monthly_metrics(df, ["product_name"])
    vol = (
        monthly.groupby("product_name")["gross_margin_pct"]
        .agg(margin_volatility_pp="std", active_months="count")
        .reset_index()
    )
    vol["margin_volatility_pp"] = vol["margin_volatility_pp"].fillna(0.0)
    products = products.merge(vol, on="product_name", how="left")
    products["margin_volatility_pp"] = products["margin_volatility_pp"].fillna(0.0)
    products["active_months"] = products["active_months"].fillna(0).astype(int)

    # Cost reduction needed to reach the benchmark at unchanged revenue.
    target_cost = (1 - margin_benchmark) * products["revenue"]
    products["cost_reduction_to_benchmark_pct"] = np.where(
        products["cost"] > 0,
        100 * np.maximum(0, products["cost"] - target_cost) / products["cost"],
        0.0,
    )
    products["below_benchmark"] = products["gross_margin_pct"] < benchmark_pct
    products["cost_heavy"] = products["cost_ratio_pct"] >= 50.0

    classifications: list[str] = []
    priorities: list[str] = []
    actions: list[str] = []
    reasons: list[str] = []
    for r in products.itertuples(index=False):
        high_sales = r.revenue_share_pct >= 5.0
        low_margin = r.gross_margin_pct < benchmark_pct
        low_sales = r.revenue_share_pct < 1.0
        low_profit = r.profit_share_pct < 0.5
        high_profit = r.profit_share_pct >= 10.0

        if high_sales and low_margin:
            classification = "High-sales / low-margin"
        elif low_sales and low_profit:
            classification = "Low-sales / low-profit"
        elif high_profit and not low_margin:
            classification = "High-profit / high-margin"
        elif low_margin:
            classification = "Margin risk"
        else:
            classification = "Core / monitor"

        if r.gross_margin_pct < 20.0 and r.revenue_share_pct >= 0.5:
            priority, action = "High", "Urgent re-source, reprice, or delist"
            reason = f"{r.gross_margin_pct:.1f}% margin and {r.cost_ratio_pct:.1f}% cost ratio."
        elif low_margin and high_sales:
            priority, action = "High", "Repricing test + supplier cost review"
            reason = f"{r.revenue_share_pct:.1f}% of revenue at only {r.gross_margin_pct:.1f}% margin."
        elif low_margin and r.revenue_share_pct >= 1.0:
            priority, action = "Medium", "Repricing / cost review"
            reason = f"Margin {r.gross_margin_pct:.1f}% is below the {benchmark_pct:.0f}% benchmark."
        elif low_margin and r.cost_heavy:
            priority, action = "Medium", "Cost renegotiation / discontinuation review"
            reason = f"Cost absorbs {r.cost_ratio_pct:.1f}% of sales; margin is {r.gross_margin_pct:.1f}%."
        elif low_margin:
            priority, action = "Medium", "Portfolio review"
            reason = f"Margin {r.gross_margin_pct:.1f}% is below the {benchmark_pct:.0f}% benchmark."
        elif high_profit and r.gross_margin_pct >= portfolio_margin:
            priority, action = "Low", "Protect supply and scale selectively"
            reason = f"{r.profit_share_pct:.1f}% of profit at {r.gross_margin_pct:.1f}% margin."
        else:
            priority, action = "Low", "Monitor"
            reason = f"Margin {r.gross_margin_pct:.1f}% meets the {benchmark_pct:.0f}% benchmark."

        classifications.append(classification)
        priorities.append(priority)
        actions.append(action)
        reasons.append(reason)

    products["classification"] = classifications
    products["risk_priority"] = priorities
    products["recommended_action"] = actions
    products["risk_reason"] = reasons
    return products.sort_values("gross_profit", ascending=False).reset_index(drop=True)


def division_metrics(df: pd.DataFrame) -> pd.DataFrame:
    div = summarize(df, ["division"])
    if div.empty:
        return div
    dist = (
        df.groupby("division")["line_margin_pct"]
        .agg(line_margin_mean_pct="mean", line_margin_std_pp="std",
             line_margin_p10_pct=lambda x: x.quantile(0.10),
             line_margin_p90_pct=lambda x: x.quantile(0.90))
        .reset_index()
    )
    dist["line_margin_std_pp"] = dist["line_margin_std_pp"].fillna(0.0)
    return div.merge(dist, on="division", how="left")


def pareto_table(products: pd.DataFrame, metric: str = "gross_profit") -> pd.DataFrame:
    if products.empty:
        return pd.DataFrame()
    out = products.sort_values(metric, ascending=False).copy()
    out["pareto_rank"] = np.arange(1, len(out) + 1)
    out["cumulative_amount"] = out[metric].cumsum()
    out["cumulative_pct"] = 100 * out["cumulative_amount"] / out[metric].sum()
    return out


def concentration_metrics(products: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {"n_products": int(len(products))}
    for label, metric in [("revenue", "revenue"), ("profit", "gross_profit")]:
        p = pareto_table(products, metric)
        if p.empty:
            continue
        shares = p[metric] / p[metric].sum()
        cum = shares.cumsum()
        n80 = int(np.searchsorted(cum.to_numpy(), 0.80) + 1)
        hhi = 10000 * float((shares ** 2).sum())
        result[f"{label}_n80"] = n80
        result[f"{label}_pct_products_for_80"] = 100 * n80 / len(p)
        result[f"{label}_top1_share_pct"] = 100 * float(shares.iloc[0])
        result[f"{label}_top3_share_pct"] = 100 * float(shares.iloc[:3].sum())
        result[f"{label}_top5_share_pct"] = 100 * float(shares.iloc[:5].sum())
        result[f"{label}_hhi"] = hhi
        result[f"{label}_effective_products"] = 10000 / hhi
        result[f"{label}_cumulative_at_n80_pct"] = 100 * float(cum.iloc[n80 - 1])
    return result


def factory_metrics(df: pd.DataFrame) -> pd.DataFrame:
    fac = summarize(df, ["factory"])
    if fac.empty:
        return fac
    return fac.merge(FACTORY_COORDS, on="factory", how="left")


def portfolio_kpis(df: pd.DataFrame, products: pd.DataFrame | None = None) -> dict[str, Any]:
    if products is None:
        products = product_metrics(df)
    revenue = float(df["sales"].sum())
    profit = float(df["gross_profit"].sum())
    cost = float(df["cost"].sum())
    units = int(df["units"].sum())
    conc = concentration_metrics(products)
    return {
        "revenue": revenue,
        "gross_profit": profit,
        "cost": cost,
        "units": units,
        "gross_margin_pct": 100 * profit / revenue if revenue else 0.0,
        "cost_ratio_pct": 100 * cost / revenue if revenue else 0.0,
        "profit_per_unit": profit / units if units else 0.0,
        "order_lines": int(len(df)),
        "orders": int(df["order_id"].nunique()),
        "products": int(df["product_name"].nunique()),
        "divisions": int(df["division"].nunique()),
        "date_min": df["order_date"].min(),
        "date_max": df["order_date"].max(),
        "top5_profit_share_pct": conc.get("profit_top5_share_pct", 0.0),
        "top5_revenue_share_pct": conc.get("revenue_top5_share_pct", 0.0),
        **{f"conc_{k}": v for k, v in conc.items()},
    }


def risk_register(products: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "product_name", "division", "factory", "revenue", "gross_profit",
        "gross_margin_pct", "cost_ratio_pct", "revenue_share_pct",
        "profit_share_pct", "cost_reduction_to_benchmark_pct",
        "risk_priority", "recommended_action", "risk_reason", "classification",
    ]
    if products.empty:
        return pd.DataFrame(columns=cols)
    out = products[cols].copy()
    out["_priority_order"] = pd.Categorical(
        out["risk_priority"], categories=["High", "Medium", "Low"], ordered=True
    )
    return (
        out.sort_values(["_priority_order", "revenue"], ascending=[True, False])
        .drop(columns="_priority_order")
        .reset_index(drop=True)
    )


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")
