# Nassau Candy — Product Line Profitability & Margin Performance Analysis

A reproducible analysis and live Streamlit application built from the supplied `Nassau Candy Distributor.csv` (10,194 order lines, 18 fields, 15 products). The project follows the Unified Mentor brief's profitability objective: product and division economics, Pareto concentration, cost diagnostics, risk flags, and an executive summary for government / public-sector stakeholders.

> **Scope reconciliation:** the brief's closing paragraph mentions "shipping route efficiency," but its problem statement, KPIs and dashboard modules are all about profitability. This project analyzes **product-line profitability** and adds a geographic/factory context section. It does **not** claim to measure route efficiency: the supplied ship dates imply 904–1,642 day lags, and all Order ID years conflict with Order Date years.

## Quick start

```bash
cd /home/user/nassau_profitability
python -m pip install -r requirements.txt
python build_deliverables.py       # rebuild all analysis outputs, figures and documents
streamlit run app.py               # launch the interactive dashboard on port 8501
```

The app is configured to bind `0.0.0.0` and work behind the Arena preview proxy. When running locally, open `http://localhost:8501`.

## Deliverables

| Deliverable | File |
|---|---|
| Executive summary for government stakeholders | `Executive_Summary_Government_Stakeholders.docx` and `.md` |
| Live Streamlit dashboard | `app.py` |
| Multi-sheet analysis workbook | `outputs/Nassau_Profitability_Analysis.xlsx` |
| Cleaned order-line data | `data/nassau_candy_clean.csv` |
| Analytical CSV / JSON exports | `outputs/` |
| Static publication figures | `outputs/figures/` |
| Shared analytic functions | `analytics.py` |
| Reproducible build pipeline | `build_deliverables.py`, `figures.py` |

## Dashboard modules and controls

- **Product overview:** margin/profit/revenue leaderboard, profit treemap, monthly trend, full KPI table.
- **Divisions:** revenue vs gross profit, weighted margin, line-margin distribution, financial efficiency index.
- **Cost & risk:** cost–sales scatter at product-month or sampled order-line granularity, price–margin and materiality–margin quadrants, dynamic risk register.
- **Concentration:** revenue and profit Pareto curves, HHI, effective SKU count, top-5 dependency indicators and state concentration.
- **Geography & factories:** regional revenue/profit/margin, state scorecard, factory coordinate map, product–factory reference table and data-integrity warning.
- **Executive brief:** key findings, decisions, public-sector interpretation and document downloads.
- **Methods & data:** KPI formulas, full source-system validation report, limitations, data preview and downloads.

Sidebar controls: **date range**, **division multiselect**, **product search**, **margin threshold slider**, and an optional restriction to products at or above the threshold. The risk register always evaluates the full date/division/search scope so low-margin products remain visible.

## Headline findings (full dataset)

- Revenue **$141,783.63**; gross profit **$93,442.80**; weighted gross margin **65.91%**; profit per unit **$2.42**.
- The five chocolate bars generate **92.88%** of revenue and **95.06%** of gross profit. Five of 15 products are required to cross 80% of either revenue or profit.
- Chocolate margin is **67.45%**; the Other division is **44.84%** with a **55.16%** cost ratio. Sugar looks efficient at **66.61%** but represents only 0.30% of revenue and 40 order lines.
- **Lickable Wallpaper** is the material high-sales/low-margin case (5.54% of revenue, 50.00% margin). **Kazookles** is the acute cost outlier (92.31% cost ratio, 7.69% margin).
- Regional margins differ by only **0.96 percentage points**; product mix, not geography, explains most margin variation.
- Monthly weighted-margin volatility is **0.53 pp**; the margin issue is structural rather than seasonal.

## Methodology

Gross margin is calculated as `Σ Gross Profit ÷ Σ Sales × 100` at each aggregation level. Profit per unit is `Σ Gross Profit ÷ Σ Units`. Margin volatility is the standard deviation of active-month weighted margins. Pareto curves rank products by revenue or profit and count the fewest products needed to cross 80%. HHI and effective-product counts measure **internal portfolio dependency**, not market concentration.

Cleaning rules implemented in `analytics.py`: trim/standardize categorical labels; preserve postal codes as text; coerce numeric fields; impute missing/nonpositive units with the product median (then global median); remove zero/invalid sales, invalid cost, and profit records that fail `Gross Profit = Sales − Cost` within $0.01; parse dates as `DD-MM-YYYY`; add line-level unit economics; and attach the brief's product–factory mapping.

Validation outcome: **no missing values, no duplicates, no zero/negative sales, no invalid profit identities, and no rows removed**. One malformed product label was normalized. Unit-imputation logic is implemented for reproducibility but was not needed.

## Important limitations

- Gross profit excludes freight, warehousing, discounts, returns, promotions, overhead, taxes and capital costs. It is not net profit.
- No price elasticity, competitor pricing, market size, channel margin, inventory or product-lifecycle data are available.
- Factory coordinates and product–factory links are reference data from the brief, not verified sourcing or route records.
- Ten products have very few order lines; their margins are descriptive rather than statistically robust.
- Operational date fields are unreliable. No delay, congestion, delivery-reliability, or route-efficiency conclusions are drawn.
- The executive summary's public-sector framing concerns supplier resilience and data quality; it does not establish market power, consumer harm or regulatory compliance.

## Reproducibility file map

```text
app.py                     live Streamlit dashboard
analytics.py               cleaning, metrics, Pareto, risk, factory functions
build_deliverables.py      orchestrates every export and document
figures.py                 static matplotlib figures
report_builder.py          DOCX + Markdown research paper and executive summary
data/                      raw copy, clean data, factory reference tables
outputs/                   CSV, JSON, XLSX and PNG analytical outputs
.streamlit/config.toml     server and theme configuration
requirements.txt           Python dependencies
```

Prepared 14 November 2026.
