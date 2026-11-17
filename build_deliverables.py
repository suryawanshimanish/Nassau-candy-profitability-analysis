"""Build every analytical export, figure, report and workbook for the project."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

from analytics import (
    CLEAN_DATA_PATH, DATA_DIR, FACTORY_COORDS, OUTPUT_DIR, PRODUCT_FACTORY, ROOT,
    concentration_metrics, division_metrics, factory_metrics, load_and_clean,
    monthly_metrics, pareto_table, portfolio_kpis, product_metrics, risk_register,
    summarize, write_json,
)
from figures import all_figures
from report_builder import build_executive_summary, build_markdown_reports, build_research_paper


def _write_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUTPUT_DIR / name, index=False)


def _excel_workbook(tables: dict[str, pd.DataFrame], kpis: dict, report: dict) -> None:
    path = OUTPUT_DIR / "Nassau_Profitability_Analysis.xlsx"
    kpi_rows = []
    for key, value in kpis.items():
        if isinstance(value, pd.Timestamp):
            value = value.date().isoformat()
        kpi_rows.append({"Metric": key, "Value": value})
    readme = pd.DataFrame(
        [
            ["Purpose", "Product-line profitability, margin performance, concentration and cost diagnostics."],
            ["Source", "Nassau Candy Distributor.csv supplied with the Unified Mentor project brief."],
            ["Scope", "Order dates 2024-01-02 through 2025-12-31; gross profit is Sales minus Cost."],
            ["Margin", "Gross profit divided by sales, aggregated as sum(profit) / sum(sales)."],
            ["Pareto", "Products ranked by revenue or profit; cumulative share is measured against that total."],
            ["Risk benchmark", "Default 60% gross margin. Actions are decision hypotheses, not automatic discontinuations."],
            ["Factory mapping", "Factory coordinates and product-factory links come from the brief, not transaction records."],
            ["Date caution", "Ship dates imply 904-1,642 day lags; no delivery-delay or route-efficiency conclusions are drawn."],
            ["Live app", "Run: streamlit run app.py"],
        ],
        columns=["Item", "Description"],
    )
    quality = pd.DataFrame(
        [{"Check": k, "Value": json.dumps(v) if isinstance(v, (dict, list)) else v} for k, v in report.items()]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        readme.to_excel(writer, sheet_name="Read me", index=False)
        pd.DataFrame(kpi_rows).to_excel(writer, sheet_name="KPI summary", index=False)
        for sheet, table in tables.items():
            table.to_excel(writer, sheet_name=sheet[:31], index=False)
        quality.to_excel(writer, sheet_name="Data quality", index=False)

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="14213D")
                cell.alignment = Alignment(vertical="center", wrap_text=True)
            ws.row_dimensions[1].height = 28
            for col in ws.columns:
                letter = col[0].column_letter
                values = [str(c.value) if c.value is not None else "" for c in col[:80]]
                width = min(max(12, max((len(v) for v in values), default=12) + 2), 48)
                ws.column_dimensions[letter].width = width
            ws.sheet_view.showGridLines = False


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "figures").mkdir(parents=True, exist_ok=True)

    df, report = load_and_clean()
    df.to_csv(CLEAN_DATA_PATH, index=False)

    products = product_metrics(df, margin_benchmark=0.60)
    divisions = division_metrics(df)
    regions = summarize(df, ["region"])
    states = summarize(df, ["state"])
    states["order_line_share_pct"] = 100 * states["order_lines"] / states["order_lines"].sum()
    states = states.sort_values("revenue", ascending=False).reset_index(drop=True)
    factories = factory_metrics(df)
    monthly = monthly_metrics(df)
    monthly_products = monthly_metrics(df, ["product_name"])
    pareto_profit = pareto_table(products, "gross_profit")
    pareto_revenue = pareto_table(products, "revenue")
    risks = risk_register(products)
    kpis = portfolio_kpis(df, products)
    concentration = concentration_metrics(products)

    region_margin_range = regions["gross_margin_pct"].max() - regions["gross_margin_pct"].min()
    state_top3 = states.head(3)["revenue_share_pct"].sum()
    kpis.update({
        "monthly_margin_volatility_pp": float(monthly["gross_margin_pct"].std()),
        "monthly_margin_min_pct": float(monthly["gross_margin_pct"].min()),
        "monthly_margin_max_pct": float(monthly["gross_margin_pct"].max()),
        "region_margin_range_pp": float(region_margin_range),
        "top3_state_revenue_share_pct": float(state_top3),
        "products_below_60pct_benchmark": int(products["below_benchmark"].sum()),
        "high_priority_products": int((products["risk_priority"] == "High").sum()),
        "other_division_cost_ratio_pct": float(divisions.loc[divisions["division"] == "Other", "cost_ratio_pct"].iloc[0]),
        "chocolate_cost_ratio_pct": float(divisions.loc[divisions["division"] == "Chocolate", "cost_ratio_pct"].iloc[0]),
    })

    exports = {
        "product_metrics.csv": products,
        "division_metrics.csv": divisions,
        "region_metrics.csv": regions,
        "state_metrics.csv": states,
        "factory_metrics.csv": factories,
        "monthly_portfolio_metrics.csv": monthly,
        "monthly_product_metrics.csv": monthly_products,
        "pareto_profit.csv": pareto_profit,
        "pareto_revenue.csv": pareto_revenue,
        "risk_register.csv": risks,
    }
    for name, table in exports.items():
        _write_csv(table, name)

    pd.DataFrame(
        [{"product_name": k, "factory": v} for k, v in PRODUCT_FACTORY.items()]
    ).to_csv(DATA_DIR / "product_factory_mapping.csv", index=False)
    FACTORY_COORDS.to_csv(DATA_DIR / "factory_coordinates.csv", index=False)

    write_json(OUTPUT_DIR / "kpi_summary.json", kpis)
    write_json(OUTPUT_DIR / "data_quality_report.json", report)
    write_json(OUTPUT_DIR / "concentration_metrics.json", concentration)

    figure_paths = all_figures(
        df=df, products=products, divisions=divisions, regions=regions,
        states=states, factories=factories, monthly=monthly,
        out_dir=OUTPUT_DIR / "figures",
    )

    workbook_tables = {
        "Product metrics": products,
        "Division metrics": divisions,
        "Region metrics": regions,
        "State metrics": states,
        "Factory metrics": factories,
        "Monthly portfolio": monthly,
        "Monthly products": monthly_products,
        "Pareto profit": pareto_profit,
        "Pareto revenue": pareto_revenue,
        "Risk register": risks,
    }
    _excel_workbook(workbook_tables, kpis, report)

    context = {
        "df": df, "products": products, "divisions": divisions, "regions": regions,
        "states": states, "factories": factories, "monthly": monthly,
        "monthly_products": monthly_products, "pareto_profit": pareto_profit,
        "pareto_revenue": pareto_revenue, "risks": risks, "kpis": kpis,
        "report": report, "concentration": concentration, "figures": figure_paths,
        "root": ROOT, "output_dir": OUTPUT_DIR,
    }
    build_research_paper(context)
    build_executive_summary(context)
    build_markdown_reports(context)

    print("Built clean data, 10 analytical CSVs, 3 JSONs, 9 figures, an Excel workbook,")
    print("a research paper (DOCX + Markdown), and an executive summary (DOCX + Markdown).")
    print(f"Portfolio: ${kpis['revenue']:,.2f} revenue | ${kpis['gross_profit']:,.2f} gross profit | {kpis['gross_margin_pct']:.2f}% margin")
    print(f"Live dashboard entry point: {ROOT / 'app.py'}")


if __name__ == "__main__":
    main()
