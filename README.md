# E-commerce Sales Analysis

An analysis of 2024 and 2025 e-commerce orders for the Wayfair scenario published by [Data Career School](https://www.datacareerschool.com/datalabs/ecommerce-sales-analysis).

## Objective

Clean the supplied data, define revenue, compare monthly sales across the two years, and identify category and product performance to inform the following year's plan.

The analysis will cover:

1. Data quality checks and a documented record of cleaning decisions.
2. An explicit definition of revenue and eligible orders.
3. Monthly revenue, year-over-year comparisons, and seasonal patterns.
4. Category revenue, monthly category mix, and best-selling products by quantity.
5. Category return and cancellation rates and average order value.
6. At least three labeled charts.
7. A one-page summary with three findings and two recommendations.

## Data and source

Download the datasets from the [original project page](https://www.datacareerschool.com/datalabs/ecommerce-sales-analysis) and place these files directly in `data/`:

- `orders.csv`
- `order_items.csv`
- `products.csv`

The exercise uses these three files. The separate customer dataset is outside scope. The order file contains a customer ID, which is not needed for this analysis. The source describes prices as USD, order timestamps as UTC, and `discount_amount` as the total discount for an order line. The company name refers to the learning scenario; this project does not independently verify the dataset's provenance as company transaction data.

Source CSV files remain unchanged. The full datasets and any cleaned record-level exports are excluded from Git through `data/`. Small public-data previews may appear in the notebook where useful. Public availability does not establish a redistribution license; obtain the datasets from the source rather than this repository.

## Project structure

```text
.
|-- .gitignore
|-- README.md
|-- requirements.txt
|-- data/                         # Ignored: source CSVs and cleaned/ exports
|-- notebooks/
|   `-- ecommerce_analysis.ipynb
`-- reports/
    |-- figures/
    `-- summary.md
```

## Setup (Windows PowerShell)

Requires Python 3.10 or newer. Run these commands from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m jupyterlab
```

Open `notebooks/ecommerce_analysis.ipynb` and select the Python kernel associated with `.venv`. In VS Code, select `.venv\Scripts\python.exe` as the notebook interpreter. Activating the environment is optional because the commands above use its executable directly.

The notebook locates `data/` relative to the project root. Run its cells in order. Setup currently includes an empty notebook outline; analysis and results will be added in later stages.

## Methodology and results

Cleaning decisions and metric definitions will be documented in the notebook before analysis. Monthly comparisons will use matching periods after checking date coverage. Figures will be saved in `reports/figures/`, and `reports/summary.md` will hold the one-page summary. Findings and recommendations will also be summarized here once verified.

## Version control

Review `git status` and staged changes before each commit. Keep source and cleaned CSVs under `data/`. Track code, documentation, useful notebook outputs, and final charts. No GitHub remote or publishing is required for local work.
