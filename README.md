# AMALO MORTGAGE INCOME & DTI DASHBOARD

Run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Interface Layout

The application opens with a top bar containing program selection and target
DTI inputs. Below the bar, the workspace is divided into three columns:

1. **Income** – borrowers, employment, self‑employment, rental, and other
   income calculators.
2. **Debts** – entry of recurring liabilities.
3. **Property** – purchase details, program fees, and save/load options.

A separate **Summary** tab consolidates housing expense, debt‑to‑income ratios,
warnings, documentation checklist, and a solver for maximum qualifying loan or
purchase price.

## Calculator Overview

The `core.calculators` module contains helpers for analyzing common mortgage
income scenarios. Each function mirrors a specific tax document or program
requirement and returns normalized monthly amounts that can be combined for
debt‑to‑income calculations.

- **W‑2 income (`w2_totals`)** – accepts year‑to‑date and prior year payroll
  data. Base pay is separated from variable overtime/bonus/commission, and a
  flag is raised when current variable income is declining.
- **Schedule C (`sch_c_totals`)** – summarizes self‑employment income from sole
  proprietors. Adds back items like depreciation and mileage while flagging
  significant year‑over‑year declines.
- **K‑1 (`k1_totals`)** – averages partnership or S‑corp income after
  adjusting for nonrecurring items and ownership percentage.
- **C‑Corporation (`ccorp_totals`)** – calculates income for borrowers who own
  100% of a corporation, accounting for add‑backs and required subtractions
  such as taxes and dividends.
- **Rental properties (`rentals_policy`)** – either derives net income from
  Schedule E or applies a market‑rent approach using 75% of gross rent minus
  PITI on the subject property.
- **Other income (`other_income_totals`)** – aggregates items like alimony or
  Social Security and optionally grosses up non‑taxable amounts.
- **Combining & qualifying (`combine_income`, `dti`, `max_affordable_pi`)** –
  merges all sources per borrower and evaluates debt‑to‑income ratios or the
  maximum affordable payment.

These explanations are also available directly in the source code as function
docstrings for quick reference in interactive environments.

## Package layout

The project separates UI from business logic to enable parallel development:

- `app.py` – Streamlit user interface and form rendering helpers.
- `core/` – reusable business logic:
  - `calculators.py` – income and qualification calculators.
  - `rules.py` – rule evaluation and warning helpers.
  - `presets.py` – program presets and constant tables.
  - `models.py` – Pydantic models describing form inputs.
- `export/` – output helpers including a `pdf_export.py` stub.

## Development

Install dependencies and run the test suite with:

```bash
pip install -r requirements.txt
pytest -q
```

New modules should live under the `core` package and include tests when
appropriate. Use `render_income_tab` helpers in `app.py` for new form groups to
maintain consistency.
