"""Generate ready-to-use project explanation content in DOCX and Markdown."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from report_builder import (
    REPORT_DATE, add_bullets, add_callout, add_caption, add_df_table, add_para,
    configure_doc, money, num, pct, set_properties, _md_table,
)
from analytics import ROOT, OUTPUT_DIR

NAVY = "14213D"
TEAL = "168AAD"
ROSE = "B54771"


def load_facts() -> dict[str, Any]:
    k = json.loads((OUTPUT_DIR / "kpi_summary.json").read_text(encoding="utf-8"))
    q = json.loads((OUTPUT_DIR / "data_quality_report.json").read_text(encoding="utf-8"))
    products = pd.read_csv(OUTPUT_DIR / "product_metrics.csv").set_index("product_name")
    divisions = pd.read_csv(OUTPUT_DIR / "division_metrics.csv").set_index("division")
    factories = pd.read_csv(OUTPUT_DIR / "factory_metrics.csv").set_index("factory")
    return {
        "k": k, "q": q, "p": products, "d": divisions, "f": factories,
        "choc": divisions.loc["Chocolate"], "other": divisions.loc["Other"],
        "sugar": divisions.loc["Sugar"], "lick": products.loc["Lickable Wallpaper"],
        "kaz": products.loc["Kazookles"], "scrum": products.loc["Wonka Bar - Scrumdiddlyumptious"],
        "nutty": products.loc["Wonka Bar - Nutty Crunch Surprise"],
        "triple": products.loc["Wonka Bar - Triple Dazzle Caramel"],
        "ever": products.loc["Everlasting Gobstopper"], "hair": products.loc["Hair Toffee"],
        "lot": factories.loc["Lot's O' Nuts"], "wicked": factories.loc["Wicked Choccy's"],
    }


def build_blocks(x: dict[str, Any]) -> list[dict[str, Any]]:
    k, q, p, d = x["k"], x["q"], x["p"], x["d"]
    choc, other, sugar = x["choc"], x["other"], x["sugar"]
    lick, kaz = x["lick"], x["kaz"]
    scrum, nutty, triple = x["scrum"], x["nutty"], x["triple"]
    lot, wicked = x["lot"], x["wicked"]

    kpi_table = pd.DataFrame([
        ["Order lines / unique orders", f"{num(k['order_lines'],0)} / {num(k['orders'],0)}"],
        ["Products / divisions", f"{k['products']} / {k['divisions']}"],
        ["Revenue", money(k["revenue"], 2)],
        ["Gross profit", money(k["gross_profit"], 2)],
        ["Weighted gross margin", pct(k["gross_margin_pct"], 2)],
        ["Profit per unit", money(k["profit_per_unit"], 2)],
        ["Top-five revenue share", pct(k["top5_revenue_share_pct"], 2)],
        ["Top-five profit share", pct(k["top5_profit_share_pct"], 2)],
        ["Monthly margin volatility", f"{num(k['monthly_margin_volatility_pp'],2)} percentage points"],
    ], columns=["Portfolio measure", "Value"])

    module_table = pd.DataFrame([
        ["Product Profitability Overview", "Margin/profit/revenue leaderboard, profit treemap, monthly trend, full product KPI table", "Reveals which products truly create value"],
        ["Division Performance Dashboard", "Revenue versus gross profit, weighted margins, line-margin distribution, profit–revenue index", "Shows structural efficiency differences"],
        ["Cost vs Margin Diagnostics", "Cost–sales scatter, price–margin and materiality–margin quadrants, risk register", "Locates pricing and sourcing problems"],
        ["Profit Concentration Analysis", "Revenue and profit Pareto curves, HHI, effective-SKU and top-five indicators", "Quantifies dependency risk"],
        ["Geography & Factory Context", "Regional/state concentration and factory coordinate map with attributed economics", "Adds resilience context without unsupported route claims"],
        ["Executive Brief & Methods", "Stakeholder findings, document downloads, validation report, formulas, limitations", "Makes the work explainable and auditable"],
    ], columns=["Module", "What it shows", "Why it matters"])

    findings_table = pd.DataFrame([
        ["Profitability is strong in aggregate", f"{pct(k['gross_margin_pct'],2)} weighted margin and {money(k['profit_per_unit'],2)} profit per unit"],
        ["Profit is highly concentrated", f"Top five products: {pct(k['top5_revenue_share_pct'],2)} of revenue, {pct(k['top5_profit_share_pct'],2)} of profit"],
        ["Divisions are structurally different", f"Chocolate {pct(choc['gross_margin_pct'],2)}; Other {pct(other['gross_margin_pct'],2)}; Sugar {pct(sugar['gross_margin_pct'],2)} but only {pct(sugar['revenue_share_pct'],2)} of revenue"],
        ["High sales can be margin-poor", f"Lickable Wallpaper: {pct(lick['revenue_share_pct'],2)} of revenue at {pct(lick['gross_margin_pct'],2)} margin"],
        ["A cost-heavy outlier exists", f"Kazookles: {pct(kaz['cost_ratio_pct'],2)} cost ratio and {pct(kaz['gross_margin_pct'],2)} margin"],
        ["Geography is not the main cause", f"Regional margins differ by {num(k['region_margin_range_pp'],2)} pp; top three states are {pct(k['top3_state_revenue_share_pct'],2)} of revenue"],
        ["Margin risk is structural", f"Monthly margin volatility is only {num(k['monthly_margin_volatility_pp'],2)} pp"],
    ], columns=["Finding", "Evidence"])

    recommendation_table = pd.DataFrame([
        ["Protect the core profit engine", "Forecast accuracy, continuity plans and margin-aware promotions for the five chocolate bars", "Top-five profit share falls from an over-concentrated level without losing core profit"],
        ["Repair material low-margin lines", "Controlled 60–90 day repricing and supplier-cost test for Lickable Wallpaper", "Measured elasticity, incremental gross profit and cannibalization"],
        ["Resolve the acute Kazookles outlier", "Cost teardown; renegotiate, redesign or begin a time-bound discontinuation review", "A viable path to the 60% benchmark, or an evidence-based exit decision"],
        ["Diversify through disciplined pilots", "Test Everlasting Gobstopper and Hair Toffee; review the nine-product micro-tail after full landed costs", "Profit sourced outside the top five increases"],
        ["Improve data governance", "Reconcile identifier and date fields; add freight, discounts, returns, promotions, inventory and channel data", "Reliable operational and financial reporting"],
    ], columns=["Recommendation", "Action", "Success measure"])

    blocks: list[dict[str, Any]] = [
        {"type": "h1", "text": "1. Project in one paragraph"},
        {"type": "p", "text":
            "The Product Line Profitability & Margin Performance Analysis for Nassau Candy Distributor converts "
            "order-line transactions into product-level financial intelligence. Instead of treating sales volume as "
            "success, the project compares revenue with manufacturing cost and gross profit to identify which products "
            "create value, which divisions underperform, where cost is excessive, and how dependent the portfolio is on "
            f"a small number of items. Using {num(k['order_lines'],0)} validated order lines, {num(k['orders'],0)} orders, "
            f"{k['products']} products and {k['divisions']} divisions, it delivers an EDA research paper, an executive "
            "summary for government/public-sector stakeholders, a supporting Excel workbook, reproducible data exports, "
            "and an interactive Streamlit dashboard."},
        {"type": "callout", "title": "One-sentence explanation",
         "text": "This project finds out which Nassau Candy products actually earn money—not just which ones sell the most—and turns that evidence into pricing, sourcing, assortment and resilience decisions."},

        {"type": "h1", "text": "2. Business context and motivation"},
        {"type": "p", "text":
            "For a distributor, revenue can be misleading. A product may have high sales because it is promoted heavily "
            "or priced low, while still contributing little profit because manufacturing cost consumes most of its "
            "selling price. Another low-volume product may have an excellent margin and deserve a controlled expansion "
            "test. Without product-level margin visibility, pricing decisions, promotions, supplier negotiations and "
            "assortment choices tend to be reactive and intuition-based."},
        {"type": "p", "text":
            "The organization therefore needs to know which product lines deliver the highest gross margin, whether "
            "high-sales products are genuinely profitable, how profitability differs across divisions, which products "
            "create margin risk, and whether the portfolio is dangerously dependent on a few items. This project "
            "answers those questions with transaction-level evidence and makes the answer explorable through a live "
            "dashboard."},

        {"type": "h1", "text": "3. Problem statement"},
        {"type": "p", "text":
            "Before the analysis, the organization lacked a consistent view of product-level gross margin, profit per "
            "unit, profit contribution, cost ratios, division efficiency, Pareto concentration and margin volatility. "
            "As a result, management could not reliably distinguish a profitable high-volume product from a "
            "cost-heavy high-volume product, or identify SKUs that should be repriced, renegotiated with suppliers, "
            "piloted for growth, or reviewed for discontinuation."},
        {"type": "callout", "title": "Core analytical question",
         "text": "Where does profit actually come from, how efficiently is revenue converted into profit, and what product or supplier decisions would improve both margin and resilience?"},

        {"type": "h1", "text": "4. Objectives"},
        {"type": "bullets", "items": [
            "Validate the transaction file and standardize product, division and date fields.",
            "Calculate gross margin, profit per unit, revenue contribution, profit contribution, cost ratio and margin volatility.",
            "Rank products by gross profit, margin, revenue and profit per unit.",
            "Identify high-profit/high-margin, high-sales/low-margin and low-sales/low-profit products.",
            "Compare revenue, profit, weighted margin and financial efficiency across divisions.",
            "Measure Pareto concentration, HHI and effective product count to detect over-dependency.",
            "Diagnose cost-heavy products and generate repricing, cost-renegotiation and discontinuation-review flags.",
            "Explain geographic volume concentration and factory attribution without making unsupported logistics claims.",
            "Deliver a live Streamlit dashboard, research paper, executive summary and reproducible analytical outputs.",
        ]},

        {"type": "h1", "text": "5. Dataset and scope"},
        {"type": "p", "text":
            f"The supplied CSV contains {q['source_rows']:,} rows and {q['source_columns']} fields. Each row is an order "
            f"line; {q['unique_orders']:,} unique Order IDs occur because one order may contain multiple products. "
            "The important fields are Order Date, Ship Date, Division, Region, State/Province, Product ID, Product Name, "
            "Sales, Units, Gross Profit and Cost. The analysis uses Order Date for the reporting period "
            f"({q['order_date_min'][:10]} to {q['order_date_max'][:10]}) because it represents commercial demand."},
        {"type": "p", "text":
            "The brief's conclusion mentions shipping-route efficiency, but its problem statement, KPIs and dashboard "
            "requirements concern product profitability. The project therefore treats profitability as the authoritative "
            "scope and offers geography/factory information only as context. This distinction matters because the "
            f"supplied ship dates imply {q['ship_days_min']:.0f}–{q['ship_days_max']:.0f} day lags, with a median of "
            f"{q['ship_days_median']:.0f} days, and all {q['order_id_year_mismatch_rows']:,} Order ID years conflict "
            "with their Order Date years. Those fields are unsuitable for route or delivery analysis."},

        {"type": "h1", "text": "6. Data cleaning and validation"},
        {"type": "p", "text":
            "The cleaning pipeline strips and standardizes labels, preserves postal codes as text, converts monetary "
            "and unit fields to numeric values, and parses dates explicitly as DD-MM-YYYY. It implements a product-median "
            "imputation rule for missing or nonpositive units, removes zero/invalid sales and invalid cost records, and "
            "rejects profit records that fail the identity Gross Profit = Sales − Cost within a $0.01 tolerance. "
            "Negative profit would be retained as a valid economic outcome; it is not treated as a data error."},
        {"type": "callout", "title": "Validation outcome",
         "text": f"All {q['clean_rows']:,} rows were retained. There were no missing values, duplicate Row IDs, exact duplicate rows, zero/negative sales, negative costs, missing units or profit-identity failures. The maximum identity error was {q['max_profit_identity_gap']:.2e}. One product label was normalized from ‘Wonka Bar -Scrumdiddlyumptious’ to ‘Wonka Bar - Scrumdiddlyumptious’."},
        {"type": "p", "text":
            "The enriched dataset adds sales per unit, cost per unit, profit per unit, line-level margin, order month, "
            "ship-day diagnostic and the factory reference supplied in the project brief. Factory links are treated as "
            "reference attributions, not verified shipment records."},

        {"type": "h1", "text": "7. Methodology and KPI logic"},
        {"type": "p", "text":
            "All aggregate margins are revenue-weighted: the sum of gross profit is divided by the sum of sales, rather "
            "than averaging percentages across rows. This prevents small transactions from distorting the portfolio "
            "result. Profit per unit divides total gross profit by total units. Revenue and profit contributions divide "
            "each product's amount by the corresponding portfolio total. Cost ratio is cost divided by sales, which is "
            "also 100 minus gross margin. Margin volatility is the standard deviation of active-month weighted margins, "
            "expressed in percentage points."},
        {"type": "p", "text":
            "Pareto analysis ranks products by revenue or gross profit and counts the fewest products needed to cross "
            "80%. HHI (10,000 × the sum of squared product shares) and effective product count (10,000 ÷ HHI) summarize "
            "dispersion. These are internal portfolio-dependency measures, not antitrust market-concentration measures. "
            "The default risk benchmark is 60% gross margin; the dashboard lets users change it dynamically."},
        {"type": "bullets", "items": [
            "High-sales product: at least 5% of revenue in the current scope.",
            "Low-margin product: below the adjustable margin benchmark.",
            "Low-sales product: below 1% of revenue; low-profit product: below 0.5% of profit.",
            "High-profit product: at least 10% of profit; cost-heavy product: at least 50% cost ratio.",
            "Risk actions are decision hypotheses, not automatic discontinuation instructions.",
        ]},

        {"type": "h1", "text": "8. Streamlit dashboard explanation"},
        {"type": "p", "text":
            "The dashboard is organized as an analytical story rather than a collection of isolated charts. The sidebar "
            "defines the scope: order date range, division selection, product search and a margin-threshold slider. "
            "The slider sets the risk benchmark and can optionally restrict the charts to products at or above it. "
            "The risk register intentionally remains visible for the full date/division/search scope so that "
            "low-margin products are not hidden."},
        {"type": "table", "data": module_table, "widths": [1.65, 3.25, 2.0], "font_size": 7.7,
         "caption": "Table 1. Dashboard modules and their explanatory purpose."},
        {"type": "p", "text":
            "Every chart and table is recalculated from the filtered order lines. Headline cards show revenue, gross "
            "profit, weighted margin, top-five profit share, products below the benchmark and the reporting period. "
            "Users can download filtered order lines, the full clean dataset, the research paper, the executive summary "
            "and the Excel workbook directly from the app. The Methods & Data tab exposes the validation report, "
            "formulas, limitations and a data preview."},

        {"type": "h1", "text": "9. What the analysis found"},
        {"type": "table", "data": kpi_table, "widths": [3.0, 3.9], "font_size": 8.6,
         "caption": "Table 2. Portfolio baseline used to explain the project."},
        {"type": "table", "data": findings_table, "widths": [2.15, 4.75], "font_size": 7.9,
         "caption": "Table 3. Principal findings and the evidence behind them."},
        {"type": "p", "text":
            f"The five chocolate bars are the profit engine. Scrumdiddlyumptious contributes the most gross profit "
            f"({money(scrum['gross_profit'],2)}, {pct(scrum['profit_share_pct'],2)} of profit), Nutty Crunch Surprise "
            f"has the strongest core margin ({pct(nutty['gross_margin_pct'],2)}), and Triple Dazzle Caramel leads "
            f"revenue ({money(triple['revenue'],2)}) despite a below-portfolio "
            f"{pct(triple['gross_margin_pct'],2)} margin. This directly demonstrates that sales rank and profitability "
            "rank are not the same."},
        {"type": "p", "text":
            f"Chocolate converts {pct(choc['revenue_share_pct'],2)} of revenue into "
            f"{pct(choc['profit_share_pct'],2)} of profit, while Other converts "
            f"{pct(other['revenue_share_pct'],2)} of revenue into only "
            f"{pct(other['profit_share_pct'],2)} of profit. Sugar appears efficient, but it represents just "
            f"{pct(sugar['revenue_share_pct'],2)} of revenue and 40 order lines, so its division-level margin should "
            "be treated as descriptive rather than robust."},
        {"type": "p", "text":
            f"Pareto analysis shows that only {k['conc_profit_n80']} of {k['products']} products are needed to cross "
            f"80% of profit. Profit HHI is {num(k['conc_profit_hhi'],0)} and the effective number of products by "
            f"profit is only {num(k['conc_profit_effective_products'],2)}. In factory terms, Lot's O' Nuts and Wicked "
            f"Choccy's together map to {pct(lot['revenue_share_pct'] + wicked['revenue_share_pct'],2)} of revenue. "
            "That is a resilience exposure, not evidence of market dominance."},
        {"type": "p", "text":
            f"Monthly weighted margin ranges only from {pct(k['monthly_margin_min_pct'],2)} to "
            f"{pct(k['monthly_margin_max_pct'],2)}, with {num(k['monthly_margin_volatility_pp'],2)} pp volatility. "
            "Product-level monthly volatility is effectively zero because unit prices and costs are nearly constant. "
            "The margin problem is therefore embedded in product economics and assortment structure, not a temporary "
            "time-based shock."},

        {"type": "h1", "text": "10. Recommendations explained"},
        {"type": "table", "data": recommendation_table, "widths": [1.65, 3.2, 2.05], "font_size": 7.7,
         "caption": "Table 4. Recommendations, actions and how success should be measured."},
        {"type": "p", "text":
            "The recommendations avoid a blanket price increase or blanket cost cut. The core products should be "
            "protected because they fund the portfolio; material low-margin products should be tested because price "
            "elasticity is unknown; severe cost outliers need a cost teardown before a discontinuation decision; and "
            "high-margin low-volume products should be piloted rather than scaled on three or four observations. "
            "Every discontinuation review should include freight, handling, returns, promotions, shelf space and "
            "contractual costs that are absent from the supplied gross-profit definition."},

        {"type": "h1", "text": "11. Government and public-sector interpretation"},
        {"type": "p", "text":
            "For a government audience, the value of the project is not that it regulates a candy distributor. It "
            "provides evidence about operational data quality, supplier and product concentration, small-supplier "
            "resilience, and the information needed for sound procurement or economic-development decisions. The "
            "executive summary therefore focuses on continuity, diversification, measured pricing action and data "
            "governance. It explicitly avoids claims about market power, consumer harm, competition-law compliance or "
            "delivery reliability because no external market-share data exist and the shipment dates are unreliable."},
        {"type": "callout", "title": "Important boundary",
         "text": "Portfolio HHI measures how dependent Nassau Candy is on its own products. It is not a market HHI and should not be used as evidence of antitrust concentration."},

        {"type": "h1", "text": "12. Limitations and responsible use"},
        {"type": "bullets", "items": [
            "Gross profit excludes freight, warehousing, discounts, returns, promotions, overhead, taxes and capital costs; it is not net profit.",
            "No price elasticity, competitor prices, market size, channel margin, inventory or product-lifecycle data are available.",
            "Ten SKUs have very few order lines, so their margins are descriptive rather than statistically robust.",
            "Factory coordinates and product–factory links are reference data from the brief, not verified sourcing records.",
            "Ship dates and Order ID years are internally inconsistent; no delay, congestion or route-efficiency conclusions are drawn.",
            "The dashboard's default 60% benchmark is a management threshold, not an industry standard; users should adjust it to the business context.",
        ]},

        {"type": "h1", "text": "13. Conclusion"},
        {"type": "p", "text":
            f"The project shows that Nassau Candy is profitable in aggregate—{pct(k['gross_margin_pct'],2)} weighted "
            "gross margin—but that the headline conceals two material risks: extreme dependence on five chocolate "
            "products and a cost-heavy tail containing Lickable Wallpaper and Kazookles. Because margin is stable over "
            "time and varies little by geography, the most effective levers are product-specific pricing, sourcing and "
            "assortment decisions. The accompanying dashboard makes those decisions transparent and repeatable, while "
            "the research paper and executive summary document the assumptions, evidence and limitations."},

        {"type": "page_break"},
        {"type": "h1", "text": "14. Two-minute presentation script"},
        {"type": "callout", "title": "Ready to speak",
         "text":
            "“This project answers a simple but important question for Nassau Candy: which products actually earn "
            "money, not just which products sell the most? We validated more than ten thousand order lines and "
            "calculated gross margin, profit per unit, contribution, cost ratios, volatility and Pareto concentration. "
            f"The portfolio earns {money(k['gross_profit'],2)} gross profit on {money(k['revenue'],2)} of sales, a "
            f"{pct(k['gross_margin_pct'],2)} weighted margin. However, five chocolate products generate "
            f"{pct(k['top5_profit_share_pct'],2)} of all profit, so the business is highly dependent on a narrow range. "
            f"The Chocolate division converts revenue efficiently at {pct(choc['gross_margin_pct'],2)} margin, while "
            f"the Other division operates at {pct(other['gross_margin_pct'],2)}. Lickable Wallpaper is the main "
            "high-sales/low-margin case, and Kazookles is a severe cost outlier. Because monthly margin volatility is "
            f"only {num(k['monthly_margin_volatility_pp'],2)} percentage points and regional margins barely differ, "
            "the problem is structural product economics rather than seasonality or geography. We recommend protecting "
            "the core range, running controlled repricing and supplier-cost tests, resolving the worst cost outlier, "
            "piloting high-margin niche products, and correcting the source-system dates before any logistics claims. "
            "The Streamlit dashboard lets stakeholders change dates, divisions, products and the margin benchmark and "
            "see every result update immediately.”"},

        {"type": "h1", "text": "15. Suggested slide flow"},
        {"type": "numbered", "items": [
            "Title and one-sentence purpose: sales volume is not profit.",
            "Business problem: why product-level margin visibility is missing.",
            "Dataset and validation: 10,194 rows, 15 products, no records removed, date caveat.",
            "Method: weighted margin, profit per unit, contribution, Pareto, cost diagnostics.",
            "Portfolio KPI snapshot: revenue, profit, margin, profit per unit.",
            "Product and division findings: core five, Other division, Lickable Wallpaper, Kazookles.",
            "Concentration and stability: Pareto, HHI, effective SKUs, low volatility.",
            "Recommendations and dashboard demonstration: filters, modules and downloads.",
        ]},

        {"type": "h1", "text": "16. Anticipated reviewer questions"},
        {"type": "qa", "items": [
            ("Why not judge products by sales alone?",
             "Because Sales does not include Cost. A high-revenue line can have a low gross margin and contribute little profit, which is exactly what happens with Lickable Wallpaper and Kazookles."),
            ("Why is gross margin weighted rather than averaged?",
             "A simple average treats a $10 order and a $1,000 order equally. Summing profit and sales first gives the actual economic margin realized by the business."),
            ("Why keep very small products in the analysis?",
             "They are needed to understand assortment complexity and tail risk. Their results are labeled descriptive, and recommendations call for pilots and full landed-cost reviews rather than immediate scaling or deletion."),
            ("What does the Pareto result mean?",
             f"Only {k['conc_profit_n80']} of {k['products']} products are required to cross 80% of profit, and the top five supply {pct(k['top5_profit_share_pct'],2)}. That creates resilience risk if demand, price or supply for those products changes."),
            ("Why does the report not evaluate shipping routes?",
             "The brief conflict is documented: ship dates imply 904–1,642 day lags and all Order ID years conflict with order dates. Reliable route analytics require corrected operational dates and shipment-level fields."),
            ("What additional data would improve the recommendations?",
             "Landed freight, discounts, returns, promotions, inventory carrying cost, customer/channel, price elasticity, supplier contracts and validated factory shipment records."),
        ]},

        {"type": "h1", "text": "17. Final takeaway"},
        {"type": "p", "text":
            "The project transforms a transactional file into a decision system: it identifies where profit is created, "
            "where it leaks, how concentrated the portfolio is, which actions deserve testing, and which claims the "
            "data cannot yet support. That combination of insight, interactivity and data honesty is the project's "
            "central contribution."},
    ]
    return blocks


def render_markdown(blocks: list[dict[str, Any]]) -> str:
    lines: list[str] = [
        "# Project Explanation Content",
        "## Product Line Profitability & Margin Performance Analysis — Nassau Candy Distributor",
        "",
        f"*Prepared {REPORT_DATE}*",
        "",
        "---",
        "",
    ]
    for b in blocks:
        t = b["type"]
        if t == "h1":
            lines += [f"## {b['text']}", ""]
        elif t == "p":
            lines += [b["text"], ""]
        elif t == "callout":
            lines += [f"> **{b['title']}.** {b['text']}", ""]
        elif t == "bullets":
            lines += [f"- {item}" for item in b["items"]] + [""]
        elif t == "numbered":
            lines += [f"{i}. {item}" for i, item in enumerate(b["items"], 1)] + [""]
        elif t == "table":
            lines += [_md_table(b["data"]), "", f"*{b['caption']}*", ""]
        elif t == "qa":
            for question, answer in b["items"]:
                lines += [f"**Q. {question}**", "", f"{answer}", ""]
        elif t == "page_break":
            lines += ["---", ""]
    lines += [
        "---",
        "",
        "*Companion files: `Research_Paper_Nassau_Candy_Profitability.docx`, "
        "`Executive_Summary_Government_Stakeholders.docx`, `app.py`, "
        "`outputs/Nassau_Profitability_Analysis.xlsx` and `README.md`.*",
        "",
    ]
    return "\n".join(lines)


def render_docx(blocks: list[dict[str, Any]], path: Path) -> None:
    doc = Document()
    configure_doc(doc)
    set_properties(doc, "Project Explanation Content — Nassau Candy Profitability",
                   "Ready-to-use narrative for reports, presentations and project walkthroughs")

    for _ in range(2):
        doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("Project Explanation Content")
    r.bold = True
    r.font.size = Pt(25)
    r.font.color.rgb = RGBColor.from_string(NAVY)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = subtitle.add_run("Product Line Profitability & Margin Performance Analysis\nNassau Candy Distributor")
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor.from_string(TEAL)
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = meta.add_run(f"Ready-to-use report, presentation and walkthrough content  |  {REPORT_DATE}")
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor.from_string("5B6573")
    doc.add_paragraph()
    add_callout(
        doc, "How to use this document",
        "Use Sections 1–13 as project-report or documentation content; Section 14 as a spoken presentation script; "
        "Section 15 as a slide outline; and Section 16 to prepare for reviewer questions. All figures come from the "
        "validated dataset and accompanying analysis outputs.",
    )
    doc.add_page_break()

    for b in blocks:
        t = b["type"]
        if t == "h1":
            doc.add_heading(b["text"], level=1)
        elif t == "p":
            add_para(doc, b["text"])
        elif t == "callout":
            add_callout(doc, b["title"], b["text"], fill="EEF4F6", accent=TEAL if b["title"] != "Important boundary" else ROSE)
        elif t == "bullets":
            add_bullets(doc, b["items"])
        elif t == "numbered":
            add_bullets(doc, b["items"], numbered=True)
        elif t == "table":
            add_df_table(doc, b["data"], widths=b.get("widths"), font_size=b.get("font_size", 8.2))
            add_caption(doc, b["caption"])
        elif t == "qa":
            for question, answer in b["items"]:
                add_para(doc, answer, lead=f"Q. {question}  ")
        elif t == "page_break":
            doc.add_page_break()
    doc.save(path)


def main() -> None:
    facts = load_facts()
    blocks = build_blocks(facts)
    md_path = ROOT / "Project_Explanation_Content.md"
    docx_path = ROOT / "Project_Explanation_Content.docx"
    md_path.write_text(render_markdown(blocks), encoding="utf-8")
    render_docx(blocks, docx_path)
    print(f"Wrote {md_path.name} and {docx_path.name}")
    print(f"Sections: {sum(1 for b in blocks if b['type']=='h1')}; blocks: {len(blocks)}")


if __name__ == "__main__":
    main()
