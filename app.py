
import json, io
import streamlit as st
import pandas as pd
from core.presets import (
    PROGRAM_PRESETS,
    CONV_MI_BANDS,
    FHA_TABLES,
    VA_TABLE,
    USDA_TABLE,
    DISCLAIMER,
    FL_DEFAULTS,
)
from core.calculators import (
    w2_totals,
    sch_c_totals,
    k1_totals,
    ccorp_totals,
    rentals_policy,
    other_income_totals,
    combine_income,
    piti_components,
    dti,
    max_affordable_pi,
    monthly_payment,
    principal_from_payment,
    nz,
)
from core.rules import evaluate_rules, has_blocking
from core.pdf_export import build_prequal_pdf


# ---------------------------------------------------------------------------
# Field guidance strings for dynamic forms. Each key corresponds to a field
# used in the income / debt entry forms and is displayed alongside the input
# control.  These mirror the guidance provided in the original Streamlit
# example and help originators locate values on borrower documents.
# ---------------------------------------------------------------------------

FIELD_GUIDANCE = {
    "BorrowerID": "Enter borrower number (1 for primary, 2 for co‑borrower).",
    "Employer": "Employer name from pay stubs or W‑2.",
    "PayType": "Salary or Hourly. Determines which base pay fields are used.",
    "AnnualSalary": "W‑2 Box 1 amount.",
    "HourlyRate": "Hourly wage from pay stub.",
    "HoursPerWeek": "Average hours worked per week.",
    "OT_YTD": "Year‑to‑date overtime earnings.",
    "Bonus_YTD": "Year‑to‑date bonus earnings.",
    "Comm_YTD": "Year‑to‑date commission earnings.",
    "Months_YTD": "Months of variable income received this year.",
    "OT_LY": "Prior year overtime earnings.",
    "Bonus_LY": "Prior year bonus earnings.",
    "Comm_LY": "Prior year commission earnings.",
    "Months_LY": "Months of variable income received last year.",
    "IncludeVariable": "Include variable income if stable.",
    "BusinessName": "Schedule C business name.",
    "Year": "Tax year for entry.",
    "NetProfit": "Schedule C Line 31.",
    "Nonrecurring": "Nonrecurring income/loss to add back.",
    "Depletion": "Schedule C Line 12.",
    "Depreciation": "Schedule C Line 13.",
    "NonDedMeals": "Schedule C Line 24b – subtract.",
    "UseOfHome": "Schedule C Line 30 – add back.",
    "AmortCasualty": "Other amortization/casualty losses – add back.",
    "BusinessMiles": "Business miles driven.",
    "MileDepRate": "Depreciation portion of IRS mileage rate.",
    "EntityName": "Partnership or S‑Corp name.",
    "Type": "1065 or 1120S entity type.",
    "OwnershipPct": "Borrower ownership percentage.",
    "Ordinary": "K‑1 Box 1 ordinary income.",
    "NetRentalOther": "K‑1 Box 2–3 income.",
    "GuaranteedPmt": "K‑1 Box 4c guaranteed payments (partnership only).",
    "NotesLT1yr": "Notes payable <1yr – subtract.",
    "NonDed_TandE": "Non‑deductible T&E – subtract.",
    "CorpName": "C‑Corporation name.",
    "TaxableIncome": "1120 Line 30 taxable income.",
    "TotalTax": "1120 Line 31 total tax.",
    "OtherIncLoss": "Other income/loss add‑backs.",
    "DividendsPaid": "Dividends paid to shareholders – subtract.",
    "Property": "Rental property identifier.",
    "Rents": "Schedule E rents received.",
    "Expenses": "Schedule E total expenses.",
    "Type_other": "Type of other income (SS, alimony, etc).",
    "GrossMonthly": "Gross monthly amount received.",
    "GrossUpPct": "Percent to gross up if non‑taxable.",
    "DebtName": "Description of debt (Car loan, etc).",
    "MonthlyPayment": "Monthly payment amount.",
    "PurchasePrice": "Subject property price.",
    "DownPaymentAmt": "Down payment amount.",
    "RatePct": "Interest rate (annual %).",
    "TermYears": "Mortgage term in years.",
    "TaxRatePct": "Annual property tax rate % of price.",
    "HOI_Annual": "Annual homeowners insurance premium.",
    "HOA_Monthly": "Monthly HOA/condo dues.",
}


# ---------------------------------------------------------------------------
# Helper widgets that display guidance text next to each input.  These closely
# mirror the layout from the example repository and provide more intuitive
# calculators for end users.
# ---------------------------------------------------------------------------

def text_input_with_help(label: str, key: str, help_key: str, value=""):
    """Text input with guidance rendered between the title and control."""

    st.markdown(f"**{label}**")
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    return st.text_input("", value=value, key=key, label_visibility="collapsed")


def number_input_with_help(
    label: str,
    key: str,
    help_key: str,
    value=0.0,
    step=1.0,
    min_value=None,
    format=None,
):
    st.markdown(f"**{label}**")
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    return st.number_input(
        "",
        value=value,
        step=step,
        min_value=min_value,
        format=format,
        key=key,
        label_visibility="collapsed",
    )


def selectbox_with_help(label: str, options: list, key: str, help_key: str, index=0):
    """Selectbox with guidance rendered between the title and control."""

    st.markdown(f"**{label}**")
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    return st.selectbox(
        "",
        options=options,
        index=index,
        key=key,
        label_visibility="collapsed",
    )


def checkbox_with_help(label: str, key: str, help_key: str):
    """Checkbox with guidance displayed between the title and control."""

    st.markdown(f"**{label}**")
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    return st.checkbox("", key=key, label_visibility="collapsed")


def borrower_select_with_help(label: str, key: str, help_key: str, value: int = 1):
    """Dropdown for selecting borrower by name while storing numeric ID."""

    ids = list(st.session_state.borrower_names.keys())
    try:
        index = ids.index(int(value))
    except Exception:
        index = 0
    st.markdown(f"**{label}**")
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    return st.selectbox(
        "",
        options=ids,
        index=index,
        key=key,
        format_func=lambda x: st.session_state.borrower_names.get(x, f"Borrower {x}"),
        label_visibility="collapsed",
    )


def render_income_tab(key_name, fields, title, show_header: bool = True):
    """Render a dynamic list of entries for a given income/debt type.

    Parameters
    ----------
    key_name: str
        Session-state key where the dynamic rows are stored.
    fields: list
        Field metadata used to render each row.
    title: str
        Human friendly title for the row group.
    show_header: bool, optional
        If ``True`` a ``subheader`` is rendered above the entries. This is
        helpful when the list is displayed inline. When embedding the list
        inside an ``st.expander`` or other container the header can be
        suppressed for a cleaner appearance.
    """

    if show_header:
        st.subheader(title)
    rows = st.session_state.get(key_name, [])
    for idx, row in enumerate(rows):
        exp = st.expander(f"{title} Entry {idx + 1}", expanded=False)
        with exp:
            if st.button("Remove", key=f"{key_name}_remove_{idx}"):
                rows.pop(idx)
                st.session_state[key_name] = rows
                st.experimental_rerun()
            cols = st.columns(3)
            for f_idx, (fname, ftype, options) in enumerate(fields):
                fkey = f"{key_name}_{idx}_{fname}"
                target = cols[f_idx % 3]
                with target:
                    if ftype == "text":
                        val = text_input_with_help(fname, fkey, fname, value=row.get(fname, ""))
                    elif ftype == "number":
                        val = number_input_with_help(
                            fname, fkey, fname, value=float(row.get(fname, 0) or 0), step=1.0
                        )
                    elif ftype == "select":
                        current = row.get(fname, options[0] if options else "")
                        try:
                            index = options.index(current)
                        except Exception:
                            index = 0
                        val = selectbox_with_help(fname, options, fkey, fname, index=index)
                    elif ftype == "checkbox":
                        val = checkbox_with_help(fname, fkey, fname)
                    elif ftype == "borrower":
                        current = int(row.get(fname, 1) or 1)
                        val = borrower_select_with_help("Borrower", fkey, "BorrowerID", value=current)
                    else:
                        val = row.get(fname)
                row[fname] = val
            rows[idx] = row

    if st.button(f"Add {title} Entry", key=f"add_{key_name}"):
        blank = {}
        for fname, ftype, opts in fields:
            if ftype == "number":
                blank[fname] = 0.0
            elif ftype == "text":
                blank[fname] = ""
            elif ftype == "select":
                blank[fname] = opts[0] if opts else ""
            elif ftype == "checkbox":
                blank[fname] = False
            elif ftype == "borrower":
                blank[fname] = 1
        rows.append(blank)
        st.session_state[key_name] = rows
        st.experimental_rerun()

st.set_page_config(page_title="AMALO MORTGAGE INCOME & DTI DASHBOARD", layout="wide")

def init_state():
    ss = st.session_state
    ss.setdefault("num_borrowers", 2)
    ss.setdefault("program", "Conventional")
    ss.setdefault("targets", PROGRAM_PRESETS["Conventional"].copy())
    ss.setdefault("fico_bucket", ">=740")
    ss.setdefault(
        "program_tables",
        {
            "conventional_mi": CONV_MI_BANDS.copy(),
            "fha": FHA_TABLES.copy(),
            "va": VA_TABLE.copy(),
            "usda": USDA_TABLE.copy(),
        },
    )
    ss.setdefault("finance_upfront", True)
    ss.setdefault("first_use_va", True)
    ss.setdefault("rental_method", "ScheduleE")
    ss.setdefault("subject_market_rent", 0.0)
    ss.setdefault("k1_verified_distributions", False)
    ss.setdefault("k1_analyzed_liquidity", False)
    ss.setdefault("support_continuance_ok", False)
    ss.setdefault("borrower_names", {1: "Borrower 1", 2: "Borrower 2"})
    # dynamic row storage for calculators
    ss.setdefault("w2_rows", [])
    ss.setdefault("schc_rows", [])
    ss.setdefault("k1_rows", [])
    ss.setdefault("c1120_rows", [])
    ss.setdefault("rental_rows", [])
    ss.setdefault("other_rows", [])
    ss.setdefault("debt_rows", [])
    ss.setdefault(
        "housing",
        {
            "purchase_price": 500000.0,
            "down_payment_amt": 100000.0,
            "rate_pct": 6.75,
            "term_years": 30,
            "tax_rate_pct": FL_DEFAULTS["tax_rate_pct"],
            "hoi_annual": FL_DEFAULTS["hoi_annual"],
            "hoa_monthly": 0.0,
        },
    )
    ss.setdefault("override_reason", "")

init_state()
# --- Application Layout Redesign ---

st.title("AMALO MORTGAGE INCOME & DTI DASHBOARD")
st.caption("Florida-friendly defaults • Program-aware calculations • Guardrails & warnings • Exports")

INCOME_FORMS = {
    "W‑2": {
        "key": "w2_rows",
        "title": "W‑2 / Base Employment",
        "guidelines": (
            "Use for salaried or hourly employees based on W‑2s or pay stubs. "
            "Include base pay and variable income when stable."
        ),
        "fields": [
            ("BorrowerID", "borrower", None),
            ("Employer", "text", None),
            ("PayType", "select", ["Salary", "Hourly"]),
            ("AnnualSalary", "number", None),
            ("HourlyRate", "number", None),
            ("HoursPerWeek", "number", None),
            ("OT_YTD", "number", None),
            ("Bonus_YTD", "number", None),
            ("Comm_YTD", "number", None),
            ("Months_YTD", "number", None),
            ("OT_LY", "number", None),
            ("Bonus_LY", "number", None),
            ("Comm_LY", "number", None),
            ("Months_LY", "number", None),
            ("IncludeVariable", "checkbox", None),
        ],
    },
    "Sch C": {
        "key": "schc_rows",
        "title": "Self‑Employed — Schedule C (two‑year analysis)",
        "guidelines": (
            "Use for sole proprietorships reporting on Schedule C. "
            "Provide two years of history and adjust for allowable add‑backs."
        ),
        "fields": [
            ("BorrowerID", "borrower", None),
            ("BusinessName", "text", None),
            ("Year", "number", None),
            ("NetProfit", "number", None),
            ("Nonrecurring", "number", None),
            ("Depletion", "number", None),
            ("Depreciation", "number", None),
            ("NonDedMeals", "number", None),
            ("UseOfHome", "number", None),
            ("AmortCasualty", "number", None),
            ("BusinessMiles", "number", None),
            ("MileDepRate", "number", None),
        ],
    },
    "K‑1": {
        "key": "k1_rows",
        "title": "K‑1 Income",
        "guidelines": (
            "Use for partnership or S‑Corporation K‑1 earnings. "
            "Verify distribution history or analyze business liquidity."
        ),
        "fields": [
            ("BorrowerID", "borrower", None),
            ("EntityName", "text", None),
            ("Year", "number", None),
            ("Type", "select", ["1065", "1120S"]),
            ("OwnershipPct", "number", None),
            ("Ordinary", "number", None),
            ("NetRentalOther", "number", None),
            ("GuaranteedPmt", "number", None),
            ("Nonrecurring", "number", None),
            ("Depreciation", "number", None),
            ("Depletion", "number", None),
            ("AmortCasualty", "number", None),
            ("NotesLT1yr", "number", None),
            ("NonDed_TandE", "number", None),
        ],
    },
}

app_tab, summary_tab = st.tabs(["Application", "Summary"])

with app_tab:
    top_cols = st.columns([2, 1, 1])
    with top_cols[0]:
        st.header("Program & Targets")
        st.session_state.program = st.selectbox("Program", list(PROGRAM_PRESETS.keys()) + ["Jumbo"])
        if st.button("Apply Program Presets"):
            preset = PROGRAM_PRESETS.get(st.session_state.program, PROGRAM_PRESETS["Conventional"])
            st.session_state.targets.update(preset)
    st.session_state.targets["FE"] = top_cols[1].number_input(
        "Target Front-End DTI %", value=float(st.session_state.targets["FE"]), step=0.5
    )
    st.session_state.targets["BE"] = top_cols[2].number_input(
        "Target Back-End DTI %", value=float(st.session_state.targets["BE"]), step=0.5
    )

    with st.expander("Borrowers"):
        st.session_state.num_borrowers = st.number_input(
            "Number of Borrowers", min_value=1, max_value=6, value=int(st.session_state.num_borrowers), step=1
        )
        for i in range(1, st.session_state.num_borrowers + 1):
            st.session_state.borrower_names[i] = st.text_input(
                f"Borrower {i} name", value=st.session_state.borrower_names.get(i, f"Borrower {i}")
            )

    income_col, debt_col, property_col = st.columns(3)

    with income_col:
        st.header("Income")
        info = INCOME_FORMS["W‑2"]
        with st.expander(info["title"]):
            st.caption(info["guidelines"])
            render_income_tab(info["key"], info["fields"], info["title"], show_header=False)
        info = INCOME_FORMS["Sch C"]
        with st.expander(info["title"]):
            st.caption(info["guidelines"])
            render_income_tab(info["key"], info["fields"], info["title"], show_header=False)
        info = INCOME_FORMS["K‑1"]
        with st.expander(info["title"]):
            st.caption(info["guidelines"])
            c1, c2 = st.columns(2)
            st.session_state.k1_verified_distributions = c1.checkbox(
                "Verified distributions history", value=bool(st.session_state.k1_verified_distributions)
            )
            st.session_state.k1_analyzed_liquidity = c2.checkbox(
                "Analyzed business liquidity (if no distributions)",
                value=bool(st.session_state.k1_analyzed_liquidity),
            )
            render_income_tab(info["key"], info["fields"], info["title"], show_header=False)
        with st.expander("Regular Corporation — 1120 (100% owner only)"):
            st.warning(
                "Only include entities where the borrower owns 100%. Entries with <100% ownership are ignored."
            )
            c1120_fields = [
                ("BorrowerID", "borrower", None),
                ("CorpName", "text", None),
                ("Year", "number", None),
                ("OwnershipPct", "number", None),
                ("TaxableIncome", "number", None),
                ("TotalTax", "number", None),
                ("Nonrecurring", "number", None),
                ("OtherIncLoss", "number", None),
                ("Depreciation", "number", None),
                ("Depletion", "number", None),
                ("AmortCasualty", "number", None),
                ("NotesLT1yr", "number", None),
                ("NonDed_TandE", "number", None),
                ("DividendsPaid", "number", None),
            ]
            render_income_tab("c1120_rows", c1120_fields, "C‑Corporation (1120)", show_header=False)
        with st.expander("Rental Income — Policy"):
            st.session_state.rental_method = st.radio(
                "Method",
                ["ScheduleE", "SeventyFivePctGross"],
                horizontal=True,
                index=0 if st.session_state.rental_method == "ScheduleE" else 1,
            )
            st.session_state.subject_market_rent = st.number_input(
                "Subject Market Rent (if applicable)",
                value=float(st.session_state.subject_market_rent),
                step=50.0,
            )
            rental_fields = [
                ("BorrowerID", "borrower", None),
                ("Property", "text", None),
                ("Year", "number", None),
                ("Rents", "number", None),
                ("Expenses", "number", None),
                ("Depreciation", "number", None),
            ]
            render_income_tab("rental_rows", rental_fields, "Rental Property", show_header=False)
        with st.expander("Other Qualifying Income"):
            other_fields = [
                ("BorrowerID", "borrower", None),
                ("Type", "text", None),
                ("GrossMonthly", "number", None),
                ("GrossUpPct", "number", None),
            ]
            render_income_tab("other_rows", other_fields, "Other Income", show_header=False)
            st.session_state.support_continuance_ok = st.checkbox(
                "Support income (if any) has ≥3 years continuance",
                value=bool(st.session_state.support_continuance_ok),
            )

    with debt_col:
        st.header("Debts")
        with st.expander("Other Recurring Debts"):
            debt_fields = [
                ("DebtName", "text", None),
                ("MonthlyPayment", "number", None),
            ]
            render_income_tab("debt_rows", debt_fields, "Debt", show_header=False)

    with property_col:
        st.header("Property")
        with st.expander("Payment & Proposed Housing", expanded=True):
            H = st.session_state.housing
            c1, c2, c3 = st.columns(3)
            H["purchase_price"] = c1.number_input(
                "Purchase Price ($)", value=float(H["purchase_price"]), step=1000.0
            )
            H["down_payment_amt"] = c2.number_input(
                "Down Payment Amount ($)", value=float(H["down_payment_amt"]), step=1000.0
            )
            H["rate_pct"] = c3.number_input(
                "Interest Rate (%)", value=float(H["rate_pct"]), step=0.125
            )
            c4, c5, c6 = st.columns(3)
            H["term_years"] = c4.number_input(
                "Term (years)", value=int(H["term_years"]), step=5
            )
            H["tax_rate_pct"] = c5.number_input(
                "Property Tax Rate (%)", value=float(H["tax_rate_pct"]), step=0.05
            )
            H["hoi_annual"] = c6.number_input(
                "Homeowners Insurance (Annual $)", value=float(H["hoi_annual"]), step=50.0
            )
            c7, c8 = st.columns(2)
            H["hoa_monthly"] = c7.number_input(
                "HOA/Condo Dues (Monthly $)", value=float(H["hoa_monthly"]), step=10.0
            )
            dp_amt = float(H["down_payment_amt"])
            base_loan = max(0.0, float(H["purchase_price"]) - dp_amt)
            conv_tbl = st.session_state.program_tables["conventional_mi"]
            fha_tbls = st.session_state.program_tables["fha"]
            va_tbl = st.session_state.program_tables["va"]
            usda_tbl = st.session_state.program_tables["usda"]
            fees = piti_components(
                st.session_state.program,
                H["purchase_price"],
                base_loan,
                H["rate_pct"],
                H["term_years"],
                H["tax_rate_pct"],
                H["hoi_annual"],
                H["hoa_monthly"],
                conv_tbl,
                fha_tbls,
                va_tbl,
                usda_tbl,
                st.session_state.finance_upfront,
                st.session_state.first_use_va,
                st.session_state.fico_bucket,
            )
            st.write(f"**Base Loan (before upfront):** ${base_loan:,.0f}")
            st.write(
                f"**Adjusted Loan (after financed fee if applicable):** ${fees['adjusted_loan']:,.0f}"
            )
            st.write(f"**LTV (base): {fees['ltv']:.2f}%**")
            st.write(
                f"**P&I:** ${fees['pi']:,.2f} | **Taxes:** ${fees['taxes']:,.2f} | **HOI:** ${fees['hoi']:,.2f} | **HOA:** ${fees['hoa']:,.2f} | **MI/MIP/Annual:** ${fees['mi']:,.2f}"
            )
            st.write(
                f"**Proposed Housing (PITI + HOA + MI): ${fees['total']:,.2f}**"
            )
        with st.expander("MI / MIP / Fees"):
            st.session_state.fico_bucket = st.selectbox(
                "FICO Bucket (display only)",
                [">=740", "720-739", "700-719", "660-699", "620-659", "<620"],
            )
            with st.expander("Conventional MI Bands (annual %) by LTV"):
                df = pd.DataFrame(
                    [{"Band": k, "AnnualPct": v} for k, v in st.session_state.program_tables["conventional_mi"].items()]
                )
                df = st.data_editor(df, use_container_width=True)
                st.session_state.program_tables["conventional_mi"] = dict(zip(df["Band"], df["AnnualPct"]))
            with st.expander("FHA Factors"):
                cols = st.columns(2)
                st.session_state.program_tables["fha"]["ufmip_pct"] = cols[0].number_input(
                    "Upfront MIP (%)",
                    value=float(st.session_state.program_tables["fha"].get("ufmip_pct", 1.75)),
                    step=0.05,
                )
                tbl = st.session_state.program_tables["fha"].get("annual_table", {})
                df = pd.DataFrame([{"Key": k, "AnnualPct": v} for k, v in tbl.items()])
                df = st.data_editor(df, use_container_width=True)
                st.session_state.program_tables["fha"]["annual_table"] = {
                    r["Key"]: r["AnnualPct"] for _, r in df.iterrows()
                }
            with st.expander("VA Funding Fee Table (%)"):
                st.session_state.first_use_va = st.checkbox(
                    "First Use", value=bool(st.session_state.first_use_va)
                )
                va = st.session_state.program_tables["va"]
                df = pd.DataFrame([{"Key": k, "Pct": v} for k, v in va.items()])
                df = st.data_editor(df, use_container_width=True)
                st.session_state.program_tables["va"] = {r["Key"]: r["Pct"] for _, r in df.iterrows()}
            with st.expander("USDA Guarantee & Annual (%)"):
                usda = st.session_state.program_tables["usda"]
                c = st.columns(2)
                usda["guarantee_pct"] = c[0].number_input(
                    "Guarantee Fee (%)", value=float(usda.get("guarantee_pct", 1.0)), step=0.05
                )
                usda["annual_pct"] = c[1].number_input(
                    "Annual Fee (%)", value=float(usda.get("annual_pct", 0.35)), step=0.05
                )
        with st.expander("Upfront Fees"):
            st.session_state.finance_upfront = st.checkbox(
                "Finance upfront fee (if applicable)", value=bool(st.session_state.finance_upfront)
            )
        with st.expander("Save / Load"):
            save_btn = st.button("Download Session JSON")
            up = st.file_uploader("Load Session JSON", type="json")
            if save_btn:
                snapshot = {k: v for k, v in st.session_state.items() if k not in ["forms"]}
                st.download_button(
                    "Download JSON",
                    data=json.dumps(snapshot, default=str),
                    file_name="session_export.json",
                    mime="application/json",
                )
            if up is not None:
                try:
                    payload = json.loads(up.read())
                    for k, v in payload.items():
                        st.session_state[k] = v
                    st.success("Session loaded.")
                except Exception as e:
                    st.error(f"Failed to load: {e}")
with summary_tab:
    st.subheader("DTI, Warnings & Checklist")
    w2_df = pd.DataFrame(st.session_state.w2_rows)
    schc_df = pd.DataFrame(st.session_state.schc_rows)
    k1_df = pd.DataFrame(st.session_state.k1_rows)
    c1120_df = pd.DataFrame(st.session_state.c1120_rows)
    rental_df = pd.DataFrame(st.session_state.rental_rows)
    other_df = pd.DataFrame(st.session_state.other_rows)
    debt_df = pd.DataFrame(st.session_state.debt_rows)
    H = st.session_state.housing
    conv_tbl = st.session_state.program_tables["conventional_mi"]
    fha_tbls = st.session_state.program_tables["fha"]
    va_tbl = st.session_state.program_tables["va"]
    usda_tbl = st.session_state.program_tables["usda"]
    fees = piti_components(
        st.session_state.program,
        H["purchase_price"],
        max(0.0, float(H["purchase_price"]) - float(H["down_payment_amt"])),
        H["rate_pct"],
        H["term_years"],
        H["tax_rate_pct"],
        H["hoi_annual"],
        H["hoa_monthly"],
        conv_tbl,
        fha_tbls,
        va_tbl,
        usda_tbl,
        st.session_state.finance_upfront,
        st.session_state.first_use_va,
        st.session_state.fico_bucket,
    )
    rentals_df = rentals_policy(
        rental_df,
        method=st.session_state.rental_method,
        subject_pitia=fees["total"],
        subject_market_rent=st.session_state.subject_market_rent,
    )
    incomes = combine_income(
        st.session_state.num_borrowers,
        w2_df,
        schc_df,
        k1_df,
        c1120_df,
        rentals_df,
        other_df,
    )
    st.dataframe(incomes, use_container_width=True)
    total_income = incomes["TotalMonthlyIncome"].sum() if not incomes.empty else 0.0
    other_debts = 0.0 if debt_df.empty else pd.to_numeric(debt_df["MonthlyPayment"], errors="coerce").fillna(0.0).sum()
    FE, BE = dti(fees["total"], fees["total"] + other_debts, total_income)
    cols = st.columns(4)
    cols[0].metric("Total Monthly Income", f"${total_income:,.2f}")
    cols[1].metric("Housing (PITIA)", f"${fees['total']:,.2f}")
    cols[2].metric("Other Debts", f"${other_debts:,.2f}")
    cols[3].metric("All Liabilities", f"${fees['total'] + other_debts:,.2f}")
    cols = st.columns(4)
    cols[0].metric("Front-End DTI", f"{FE*100:.2f}%", delta="PASS" if (FE*100) <= float(st.session_state.targets['FE']) else "CHECK")
    cols[1].metric("Back-End DTI", f"{BE*100:.2f}%", delta="PASS" if (BE*100) <= float(st.session_state.targets['BE']) else "CHECK")
    cols[2].metric("Target FE", f"{st.session_state.targets['FE']:.2f}%")
    cols[3].metric("Target BE", f"{st.session_state.targets['BE']:.2f}%")
    w2_included_lt_12 = False
    if not w2_df.empty:
        months = pd.to_numeric(w2_df['Months_YTD'], errors='coerce').fillna(0) + pd.to_numeric(w2_df['Months_LY'], errors='coerce').fillna(0)
        included = pd.to_numeric(w2_df['IncludeVariable'], errors='coerce').fillna(0) == 1
        if any((months < 12) & included):
            w2_included_lt_12 = True
    w2_declining_flag = bool(incomes.get('AnyDecliningFlag', pd.Series([False])).any())
    schc_declining = bool(incomes.get('SchC_DecliningFlag', pd.Series([False])).any())
    uses_k1 = not k1_df.empty
    uses_c1120 = not c1120_df.empty
    c1120_any_lt_100 = False
    if uses_c1120:
        own = pd.to_numeric(c1120_df['OwnershipPct'], errors='coerce').fillna(0)
        c1120_any_lt_100 = any(own < 100)
    uses_support_income = (
        any(other_df['Type'].astype(str).str.lower().str.contains('alimony|child', regex=True))
        if not other_df.empty
        else False
    )
    rental_method_conflict = False
    sanity_inputs_out_of_band = False
    if st.session_state.housing['purchase_price'] > 0:
        annual_non_PI = (fees['taxes'] + fees['hoi'] + fees['hoa'] + fees['mi']) * 12
        if annual_non_PI > 0.05 * st.session_state.housing['purchase_price']:
            sanity_inputs_out_of_band = True
    rule_state = {
        "total_income": total_income,
        "FE": FE,
        "BE": BE,
        "target_FE": st.session_state.targets['FE'],
        "target_BE": st.session_state.targets['BE'],
        "w2_meta": {"var_included_lt_12": w2_included_lt_12, "declining_var": w2_declining_flag},
        "schc_declining": schc_declining,
        "uses_k1": uses_k1,
        "k1_verified_distributions": st.session_state.k1_verified_distributions,
        "k1_analyzed_liquidity": st.session_state.k1_analyzed_liquidity,
        "uses_c1120": uses_c1120,
        "c1120_any_lt_100": c1120_any_lt_100,
        "uses_support_income": uses_support_income,
        "support_continuance_ok": st.session_state.support_continuance_ok,
        "rental_method_conflict": rental_method_conflict,
        "sanity_inputs_out_of_band": sanity_inputs_out_of_band,
    }
    rule_results = evaluate_rules(rule_state)
    if rule_results:
        for r in rule_results:
            if r.severity == "critical":
                st.error(f"[{r.code}] {r.message}")
            elif r.severity == "warn":
                st.warning(f"[{r.code}] {r.message}")
            else:
                st.info(f"[{r.code}] {r.message}")
    else:
        st.success("No warnings.")
    st.divider()
    checklist = []
    if not w2_df.empty:
        checklist += [
            {"label": "Most recent paystubs (30 days)", "checked": False},
            {"label": "W-2s (2 years)", "checked": False},
            {"label": "VOE (verbal/written)", "checked": False},
        ]
    if not schc_df.empty or not k1_df.empty or not c1120_df.empty:
        checklist += [
            {"label": "Personal tax returns (2 years)", "checked": False},
            {"label": "Business returns (K-1/1065/1120S/1120)", "checked": False},
        ]
    if st.session_state.k1_verified_distributions or st.session_state.k1_analyzed_liquidity:
        checklist += [
            {"label": "K-1 distributions evidence or business liquidity analysis", "checked": True}
        ]
    if not rental_df.empty:
        checklist += [
            {"label": "Leases / Market rent report", "checked": False},
            {"label": "Schedule E pages", "checked": False},
        ]
    if uses_support_income:
        checklist += [
            {
                "label": "Court order + proof of receipt + ≥3 years continuance",
                "checked": st.session_state.support_continuance_ok,
            }
        ]
    if not other_df.empty:
        checklist += [
            {"label": "Evidence of receipt/continuance for other income", "checked": False}
        ]
    if not checklist:
        checklist = [{"label": "Standard disclosures", "checked": False}]
    st.write("**Documentation Checklist**")
    for i, item in enumerate(checklist):
        checklist[i]["checked"] = st.checkbox(item["label"], value=item["checked"], key=f"chk_{i}")
    st.divider()
    st.write("**Disclaimer**")
    st.caption(DISCLAIMER)
    st.divider()
    c1, c2, c3 = st.columns([2, 1, 1])
    blocking = has_blocking(rule_results)
    if blocking:
        st.error("Critical warnings present. Provide an override reason to enable PDF export.")
        st.session_state.override_reason = c1.text_input(
            "Override reason (will be embedded in PDF)", value=st.session_state.override_reason
        )
    else:
        st.session_state.override_reason = ""

    def make_csv_bytes():
        buf = io.StringIO()
        summary = pd.DataFrame(
            [
                {
                    "Program": st.session_state.program,
                    "PurchasePrice": st.session_state.housing['purchase_price'],
                    "DownPayment": st.session_state.housing['down_payment_amt'],
                    "AdjustedLoan": fees['adjusted_loan'],
                    "P&I": fees['pi'],
                    "Taxes": fees['taxes'],
                    "HOI": fees['hoi'],
                    "HOA": fees['hoa'],
                    "MI_MIP": fees['mi'],
                    "HousingTotal": fees['total'],
                    "TotalIncome": total_income,
                    "OtherDebts": other_debts,
                    "FrontEndDTI_pct": FE * 100,
                    "BackEndDTI_pct": BE * 100,
                    "Targets_FE_BE": f"{st.session_state.targets['FE']}/{st.session_state.targets['BE']}",
                }
            ]
        )
        summary.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")

    st.download_button(
        "Download CSV Summary",
        data=make_csv_bytes(),
        file_name="prequal_summary.csv",
        mime="text/csv",
    )
    if (not blocking) or (blocking and st.session_state.override_reason.strip()):
        if c2.button("Export Prequal PDF"):
            path = "prequal_summary.pdf"
            header = ["Borrower"] + [c for c in ["W2", "SchC", "K1", "1120", "Rental", "Other", "Total"]]
            rows = [header]
            for _, row in incomes.iterrows():
                bid = int(row['BorrowerID'])
                name = st.session_state.borrower_names.get(bid, f"Borrower {bid}")
                rows.append([
                    name,
                    f"${row['W2_Monthly']:,.2f}",
                    f"${row['SchC_Monthly']:,.2f}",
                    f"${row['K1_Monthly']:,.2f}",
                    f"${row['C1120_Monthly']:,.2f}",
                    f"${row['Rental_Monthly']:,.2f}",
                    f"${row['Other_Monthly']:,.2f}",
                    f"${row['TotalMonthlyIncome']:,.2f}",
                ])
            warn_export = [{"code": r.code, "severity": r.severity, "message": r.message} for r in rule_results]
            if st.session_state.override_reason.strip():
                warn_export.append({
                    "code": "OVERRIDE",
                    "severity": "info",
                    "message": f"Override reason: {st.session_state.override_reason.strip()}",
                })
            snapshot = {
                "deal_snapshot": {
                    "Program": st.session_state.program,
                    "Rate / Term": f"{st.session_state.housing['rate_pct']}% / {st.session_state.housing['term_years']} yrs",
                    "Purchase Price": f"${st.session_state.housing['purchase_price']:,.0f}",
                    "Down Payment": f"${st.session_state.housing['down_payment_amt']:,.0f}",
                    "LTV (base)": f"{fees['ltv']:.2f}%",
                    "Financed Upfront?": "Yes" if st.session_state.finance_upfront else "No",
                },
                "totals": {
                    "P&I": f"${fees['pi']:,.2f}",
                    "Taxes": f"${fees['taxes']:,.2f}",
                    "HOI": f"${fees['hoi']:,.2f}",
                    "HOA": f"${fees['hoa']:,.2f}",
                    "MI/MIP": f"${fees['mi']:,.2f}",
                    "Housing (PITIA)": f"${fees['total']:,.2f}",
                    "Total Income": f"${total_income:,.2f}",
                    "Front-End DTI": f"{FE*100:.2f}%",
                    "Back-End DTI": f"{BE*100:.2f}%",
                    "Targets (FE/BE)": f"{st.session_state.targets['FE']}% / {st.session_state.targets['BE']}%",
                },
            }
            branding = {
                "title": "Prequalification Summary",
                "mlo": ", ".join(n for n in st.session_state.borrower_names.values() if n),
                "contact": "",
                "nmls": "",
            }
            build_prequal_pdf(path, branding, snapshot, rows, warn_export, checklist)
            with open(path, "rb") as f:
                st.download_button(
                    "Download PDF",
                    data=f.read(),
                    file_name="prequal_summary.pdf",
                    mime="application/pdf",
                )
    else:
        c3.info("Resolve critical warnings or add an override reason to enable PDF export.")
    st.subheader("Max Purchase / Max Loan Solver")
    try:
        incomes = combine_income(
            st.session_state.num_borrowers,
            pd.DataFrame(st.session_state.w2_rows),
            pd.DataFrame(st.session_state.schc_rows),
            pd.DataFrame(st.session_state.k1_rows),
            pd.DataFrame(st.session_state.c1120_rows),
            rentals_policy(
                pd.DataFrame(st.session_state.rental_rows),
                st.session_state.rental_method,
                st.session_state.subject_market_rent,
            ),
            pd.DataFrame(st.session_state.other_rows),
        )
        total_income = incomes['TotalMonthlyIncome'].sum()
    except Exception:
        total_income = 0.0
    rate = st.number_input(
        "Rate (%)", value=float(st.session_state.housing['rate_pct']), step=0.125, key="solver_rate"
    )
    term = st.number_input(
        "Term (years)", value=int(st.session_state.housing['term_years']), step=5, key="solver_term"
    )
    taxes_ins_hoa_mi = st.number_input(
        "Taxes + Insurance + HOA + MI (monthly)", value=0.0, step=25.0
    )
    debt_df = pd.DataFrame(st.session_state.debt_rows)
    other_debts = 0.0 if debt_df.empty else pd.to_numeric(debt_df['MonthlyPayment'], errors='coerce').fillna(0.0).sum()
    targets = st.session_state.targets
    fe_max, be_max, conservative_pi = max_affordable_pi(total_income, other_debts, taxes_ins_hoa_mi, targets['FE'], targets['BE'])
    max_loan = principal_from_payment(conservative_pi, rate, term)
    dp_pct = st.number_input("Down Payment %", value=20.0, step=1.0)
    max_purchase = max_loan / (1 - dp_pct / 100.0) if dp_pct < 100 else max_loan
    c1, c2, c3 = st.columns(3)
    c1.metric("Conservative Max P&I", f"${conservative_pi:,.2f}")
    c2.metric("Max Base Loan", f"${max_loan:,.0f}")
    c3.metric("Max Purchase (given DP%)", f"${max_purchase:,.0f}")
