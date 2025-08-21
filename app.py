
import json, io
import re
import streamlit as st
import pandas as pd
from streamlit.components.v1 import html
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
    default_gross_up_pct,
    filter_support_income,
)
from core.rules import evaluate_rules, has_blocking
from export.pdf_export import build_prequal_pdf
from core.models import (
    W2,
    SchC,
    K1,
    C1120,
    Rental,
    OtherIncome,
    Debt,
)


# ---------------------------------------------------------------------------
# Utility helpers for UI polish and scroll preservation
# ---------------------------------------------------------------------------


def pretty_label(label: str) -> str:
    """Convert field keys to more readable labels."""

    label = re.sub(r"(_|-)+", " ", label)
    return re.sub(r"(?<!^)(?=[A-Z])", " ", label).strip()


def _persist_scroll():
    """Store and restore scroll position without forcing reruns."""

    html(
        """
        <script>
        const pos = sessionStorage.getItem('scrollPos');
        if (pos) window.scrollTo(0, parseInt(pos));
        window.addEventListener('scroll', () => {
            sessionStorage.setItem('scrollPos', window.scrollY);
        });
        </script>
        """,
        height=0,
    )


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
    "VarAvgMonths": "Averaging period for variable income (12 vs 24 months).",
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

FIELD_DOC_LINKS = {
    "AnnualSalary": "https://www.irs.gov/pub/irs-pdf/fw2.pdf",
    "NetProfit": "https://www.irs.gov/pub/irs-pdf/f1040sc.pdf",
}

# ---------------------------------------------------------------------------
# Form field definitions and rendering helpers for various income and debt
# categories.  Each function wraps the generic ``render_income_tab``
# component with fields specific to that income type.  Pydantic models from
# ``core.models`` provide typed defaults when adding new rows.
# ---------------------------------------------------------------------------

W2_FIELDS = [
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
    ("VarAvgMonths", "select", [12, 24]),
    ("IncludeVariable", "checkbox", None),
]
W2_GUIDELINES = (
    "Use for salaried or hourly employees based on W‑2s or pay stubs. "
    "Include base pay and variable income when stable."
)

SCHC_FIELDS = [
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
]
SCHC_GUIDELINES = (
    "Use for sole proprietorships reporting on Schedule C. Provide two years of "
    "history and adjust for allowable add‑backs."
)

K1_FIELDS = [
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
]
K1_GUIDELINES = (
    "Use for partnership or S‑Corporation K‑1 earnings. Verify distribution "
    "history or analyze business liquidity."
)

C1120_FIELDS = [
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

RENTAL_FIELDS = [
    ("BorrowerID", "borrower", None),
    ("Property", "text", None),
    ("Year", "number", None),
    ("Rents", "number", None),
    ("Expenses", "number", None),
    ("Depreciation", "number", None),
]

OTHER_FIELDS = [
    ("BorrowerID", "borrower", None),
    ("Type", "text", None),
    ("GrossMonthly", "number", None),
    ("GrossUpPct", "number", None),
]

DEBT_FIELDS = [
    ("DebtName", "text", None),
    ("MonthlyPayment", "number", None),
]


def render_w2_form():
    st.caption(W2_GUIDELINES)
    rows = st.session_state.get("w2_rows", [])
    if st.button("Add W-2 Job", key="add_w2_job"):
        rows.append(W2().model_dump())
        st.session_state["w2_rows"] = rows
    for idx, row in enumerate(rows):
        title = row.get("Employer") or f"Job {idx + 1}"
        with st.container():
            st.subheader(title)
            form_key = f"w2_job_{idx}"
            with st.form(form_key):
                cols = st.columns(3)
                for f_idx, (fname, ftype, options) in enumerate(W2_FIELDS):
                    fkey = f"{form_key}_{fname}"
                    target = cols[f_idx % 3]
                    with target:
                        if ftype == "text":
                            sugg = st.session_state.get("employer_suggestions", []) if fname == "Employer" else None
                            val = text_input_with_help(
                                fname, fkey, fname, value=row.get(fname, ""), suggestions=sugg
                            )
                            if fname == "Employer" and val and val not in st.session_state.employer_suggestions:
                                st.session_state.employer_suggestions.append(val)
                        elif ftype == "number":
                            val = number_input_with_help(
                                fname,
                                fkey,
                                fname,
                                value=float(row.get(fname, 0) or 0),
                                step=1.0,
                                min_value=0.0,
                            )
                            if fname == "HoursPerWeek" and str(row.get("PayType", "")).lower() == "hourly":
                                monthly = float(row.get("HourlyRate", 0)) * val * 52 / 12
                                st.caption(f"Monthly base pay: ${monthly:,.2f}")
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

                preview = w2_totals(pd.DataFrame([row]))
                if not preview.empty:
                    bm = float(preview.loc[0, "BaseMonthly"])
                    vm = float(preview.loc[0, "VariableMonthly"])
                    qm = float(preview.loc[0, "QualMonthly"])
                    st.caption(
                        f"BaseMonthly: ${bm:,.2f} | VariableMonthly: ${vm:,.2f} | QualMonthly: ${qm:,.2f}"
                    )
                    if (row.get("Months_YTD", 0) + row.get("Months_LY", 0)) < 12:
                        st.warning(
                            "Fewer than 12 months of variable income reported. Consider excluding variable income or obtaining more history."
                        )

                c1, c2 = st.columns(2)
                save = c1.form_submit_button("Save")
                remove = c2.form_submit_button("Remove")

            if save:
                rows[idx] = row
                st.session_state["w2_rows"] = rows
            if remove:
                rows.pop(idx)
                st.session_state["w2_rows"] = rows


def render_schedule_c_form():
    st.caption(SCHC_GUIDELINES)
    render_income_tab("schc_rows", SCHC_FIELDS, "Self‑Employed — Schedule C (two‑year analysis)", model_cls=SchC, show_header=False)


def render_k1_form():
    st.caption(K1_GUIDELINES)
    c1, c2 = st.columns(2)
    st.session_state.k1_verified_distributions = c1.checkbox(
        "Verified distributions history", value=bool(st.session_state.k1_verified_distributions)
    )
    st.session_state.k1_analyzed_liquidity = c2.checkbox(
        "Analyzed business liquidity (if no distributions)",
        value=bool(st.session_state.k1_analyzed_liquidity),
    )
    st.session_state.k1_justification = st.text_area(
        "Underwriter justification",
        value=st.session_state.k1_justification,
    )
    render_income_tab("k1_rows", K1_FIELDS, "K‑1 Income", model_cls=K1, show_header=False)


def render_corp1120_form():
    st.warning(
        "C‑Corp income counts only if ownership is 100%. Entries with lower ownership are ignored and inputs disabled."
    )
    def disabler(row, fname):
        if fname == "OwnershipPct":
            return False
        try:
            return float(row.get("OwnershipPct", 0) or 0) < 100
        except Exception:
            return True
    render_income_tab(
        "c1120_rows",
        C1120_FIELDS,
        "C‑Corporation (1120)",
        model_cls=C1120,
        show_header=False,
        disable_fn=disabler,
    )


def render_rental_form():
    st.session_state.rental_method = st.radio(
        "Method",
        ["ScheduleE", "SeventyFivePctGross"],
        horizontal=True,
        index=0 if st.session_state.rental_method == "ScheduleE" else 1,
    )
    if st.session_state.rental_method == "ScheduleE":
        st.info("Using Schedule E net income")
    else:
        st.info("Using 75% of gross rents")
    st.session_state.subject_market_rent = st.number_input(
        "Subject Market Rent (if applicable)",
        value=float(st.session_state.subject_market_rent),
        step=50.0,
    )
    st.session_state.subject_pitia = st.number_input(
        "Subject PITIA (if applicable)",
        value=float(st.session_state.subject_pitia),
        step=50.0,
    )
    render_income_tab(
        "rental_rows", RENTAL_FIELDS, "Rental Property", model_cls=Rental, show_header=False
    )


def render_other_income_form():
    render_income_tab("other_rows", OTHER_FIELDS, "Other Income", model_cls=OtherIncome, show_header=False)
    rows = st.session_state.get("other_rows", [])
    for row in rows:
        default = default_gross_up_pct(row.get("Type", ""), st.session_state.program)
        if nz(row.get("GrossUpPct")) == 0 and default:
            row["GrossUpPct"] = default
    st.session_state.other_rows = rows
    st.session_state.support_continuance_ok = st.checkbox(
        "Alimony/child support/housing allowance has ≥3 years continuance",
        value=bool(st.session_state.support_continuance_ok),
    )


def render_debt_form():
    render_income_tab("debt_rows", DEBT_FIELDS, "Debt", model_cls=Debt, show_header=False)


# ---------------------------------------------------------------------------
# Helper widgets that display guidance text next to each input.  These closely
# mirror the layout from the example repository and provide more intuitive
# calculators for end users.
# ---------------------------------------------------------------------------

def text_input_with_help(label: str, key: str, help_key: str, value="", suggestions=None, disabled: bool = False):
    """Text input with guidance rendered between the title and control."""

    disp = pretty_label(label)
    st.markdown(f"<span title='{disp}'><strong>{disp}</strong></span>", unsafe_allow_html=True)
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    link = FIELD_DOC_LINKS.get(help_key)
    if link:
        st.markdown(f"<a href='{link}' target='_blank'>📄</a>", unsafe_allow_html=True)
    val = st.text_input("", value=value, key=key, label_visibility="collapsed", disabled=disabled)
    if suggestions:
        pick = st.selectbox(
            "", [""] + suggestions, key=f"{key}_suggest", label_visibility="collapsed", disabled=disabled
        )
        if pick:
            val = pick
            st.session_state[key] = val
    return val


def number_input_with_help(
    label: str,
    key: str,
    help_key: str,
    value=0.0,
    step=1.0,
    min_value=None,
    format=None,
    disabled: bool = False,
):
    disp = pretty_label(label)
    st.markdown(f"<span title='{disp}'><strong>{disp}</strong></span>", unsafe_allow_html=True)
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    link = FIELD_DOC_LINKS.get(help_key)
    if link:
        st.markdown(f"<a href='{link}' target='_blank'>📄</a>", unsafe_allow_html=True)
    return st.number_input(
        "",
        value=value,
        step=step,
        min_value=min_value,
        format=format,
        key=key,
        label_visibility="collapsed",
        disabled=disabled,
    )


def selectbox_with_help(label: str, options: list, key: str, help_key: str, index=0, disabled: bool = False):
    """Selectbox with guidance rendered between the title and control."""

    disp = pretty_label(label)
    st.markdown(f"<span title='{disp}'><strong>{disp}</strong></span>", unsafe_allow_html=True)
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    link = FIELD_DOC_LINKS.get(help_key)
    if link:
        st.markdown(f"<a href='{link}' target='_blank'>📄</a>", unsafe_allow_html=True)
    return st.selectbox(
        "",
        options=options,
        index=index,
        key=key,
        label_visibility="collapsed",
        disabled=disabled,
    )


def checkbox_with_help(label: str, key: str, help_key: str, disabled: bool = False):
    """Checkbox with guidance displayed between the title and control."""

    disp = pretty_label(label)
    st.markdown(f"<span title='{disp}'><strong>{disp}</strong></span>", unsafe_allow_html=True)
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    link = FIELD_DOC_LINKS.get(help_key)
    if link:
        st.markdown(f"<a href='{link}' target='_blank'>📄</a>", unsafe_allow_html=True)
    return st.checkbox("", key=key, label_visibility="collapsed", disabled=disabled)


def borrower_select_with_help(label: str, key: str, help_key: str, value: int = 1, disabled: bool = False):
    """Dropdown for selecting borrower by name while storing numeric ID."""

    ids = list(st.session_state.borrower_names.keys())
    try:
        index = ids.index(int(value))
    except Exception:
        index = 0
    disp = pretty_label(label)
    st.markdown(f"<span title='{disp}'><strong>{disp}</strong></span>", unsafe_allow_html=True)
    help = FIELD_GUIDANCE.get(help_key, "")
    if help:
        st.caption(help)
    link = FIELD_DOC_LINKS.get(help_key)
    if link:
        st.markdown(f"<a href='{link}' target='_blank'>📄</a>", unsafe_allow_html=True)
    return st.selectbox(
        "",
        options=ids,
        index=index,
        key=key,
        format_func=lambda x: st.session_state.borrower_names.get(x, f"Borrower {x}"),
        label_visibility="collapsed",
        disabled=disabled,
    )


def render_income_tab(key_name, fields, title, model_cls=None, show_header: bool = True, disable_fn=None):
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
        container = st.container()
        with container:
            st.markdown(f"**{title} Entry {idx + 1}**")
            if st.button("Remove", key=f"{key_name}_remove_{idx}"):
                rows.pop(idx)
                st.session_state[key_name] = rows
            cols = st.columns(2)
            for f_idx, (fname, ftype, options) in enumerate(fields):
                fkey = f"{key_name}_{idx}_{fname}"
                target = cols[f_idx % 2]
                with target:
                    disabled = disable_fn(row, fname) if disable_fn else False
                    if ftype == "text":
                        sugg = None
                        if fname == "Employer":
                            sugg = st.session_state.get("employer_suggestions", [])
                        elif fname == "BusinessName":
                            sugg = st.session_state.get("business_suggestions", [])
                        val = text_input_with_help(
                            fname, fkey, fname, value=row.get(fname, ""), suggestions=sugg, disabled=disabled
                        )
                        if fname == "Employer" and val and val not in st.session_state.employer_suggestions:
                            st.session_state.employer_suggestions.append(val)
                        if fname == "BusinessName" and val and val not in st.session_state.business_suggestions:
                            st.session_state.business_suggestions.append(val)
                    elif ftype == "number":
                        val = number_input_with_help(
                            fname, fkey, fname, value=float(row.get(fname, 0) or 0), step=1.0, disabled=disabled
                        )
                    elif ftype == "select":
                        current = row.get(fname, options[0] if options else "")
                        try:
                            index = options.index(current)
                        except Exception:
                            index = 0
                        val = selectbox_with_help(fname, options, fkey, fname, index=index, disabled=disabled)
                    elif ftype == "checkbox":
                        val = checkbox_with_help(fname, fkey, fname, disabled=disabled)
                    elif ftype == "borrower":
                        current = int(row.get(fname, 1) or 1)
                        val = borrower_select_with_help("Borrower", fkey, "BorrowerID", value=current, disabled=disabled)
                    else:
                        val = row.get(fname)
                row[fname] = val
            rows[idx] = row
        st.divider()

    if st.button(f"Add {title} Entry", key=f"add_{key_name}"):
        if model_cls is not None:
            blank = model_cls().model_dump()
        else:
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

st.set_page_config(page_title="AMALO MORTGAGE INCOME & DTI DASHBOARD", layout="wide")
_persist_scroll()

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
    ss.setdefault("subject_pitia", 0.0)
    ss.setdefault("k1_verified_distributions", False)
    ss.setdefault("k1_analyzed_liquidity", False)
    ss.setdefault("k1_justification", "")
    ss.setdefault("selfemp_year_mode", "average")
    ss.setdefault("support_continuance_ok", False)
    ss.setdefault(
        "borrower_names", {i: f"Borrower {i}" for i in range(1, 5)}
    )
    ss.setdefault("employer_suggestions", [])
    ss.setdefault("business_suggestions", [])
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
# --- Navigation & Layout ---

def compute_results():
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
    subj_pitia = st.session_state.subject_pitia or fees["total"]
    st.session_state.subject_pitia = subj_pitia
    rentals_df = rentals_policy(
        rental_df,
        method=st.session_state.rental_method,
        subject_pitia=subj_pitia,
        subject_market_rent=st.session_state.subject_market_rent,
    )
    recent_selfemp = st.session_state.selfemp_year_mode != "average"
    k1_allowed = st.session_state.k1_verified_distributions or st.session_state.k1_analyzed_liquidity
    k1_input = k1_df if (not k1_df.empty and k1_allowed) else None
    uses_support_income = (
        any(
            other_df["Type"].astype(str).str.lower().str.contains(
                "alimony|child|housing", regex=True
            )
        )
        if not other_df.empty
        else False
    )
    other_df = filter_support_income(other_df, st.session_state.support_continuance_ok)
    incomes = combine_income(
        st.session_state.num_borrowers,
        w2_df,
        schc_df,
        k1_input,
        c1120_df,
        rentals_df,
        other_df,
        recent_selfemp=recent_selfemp,
    )
    total_income = incomes["TotalMonthlyIncome"].sum() if not incomes.empty else 0.0
    other_debts = 0.0 if debt_df.empty else pd.to_numeric(debt_df["MonthlyPayment"], errors="coerce").fillna(0.0).sum()
    FE, BE = dti(fees["total"], fees["total"] + other_debts, total_income)
    w2_included_lt_12 = False
    if not w2_df.empty:
        months = pd.to_numeric(w2_df['Months_YTD'], errors='coerce').fillna(0) + pd.to_numeric(w2_df['Months_LY'], errors='coerce').fillna(0)
        included = pd.to_numeric(w2_df['IncludeVariable'], errors='coerce').fillna(0) == 1
        if any((months < 12) & included):
            w2_included_lt_12 = True
    w2_var_declining = bool(incomes.get('W2_DecliningVarFlag', pd.Series([False])).any())
    w2_base_declining = bool(incomes.get('W2_DecliningBaseFlag', pd.Series([False])).any())
    schc_declining = bool(incomes.get('SchC_DecliningFlag', pd.Series([False])).any())
    k1_declining = bool(incomes.get('K1_DecliningFlag', pd.Series([False])).any())
    c1120_declining = bool(incomes.get('C1120_DecliningFlag', pd.Series([False])).any())
    rental_declining = bool(incomes.get('Rental_DecliningFlag', pd.Series([False])).any())
    uses_k1 = not k1_df.empty
    uses_c1120 = not c1120_df.empty
    c1120_any_lt_100 = False
    if uses_c1120:
        own = pd.to_numeric(c1120_df['OwnershipPct'], errors='coerce').fillna(0)
        c1120_any_lt_100 = any(own < 100)
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
        "w2_meta": {"var_included_lt_12": w2_included_lt_12, "declining_var": w2_var_declining, "declining_base": w2_base_declining},
        "schc_declining": schc_declining,
        "k1_declining": k1_declining,
        "c1120_declining": c1120_declining,
        "rental_declining": rental_declining,
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
    blocking = has_blocking(rule_results)
    checklist = []
    if w2_included_lt_12:
        checklist.append({"label": "W‑2 variable income <12 months but included", "checked": False})
    if uses_k1:
        checklist.append({"label": "K‑1 distribution history or liquidity analyzed", "checked": st.session_state.k1_verified_distributions or st.session_state.k1_analyzed_liquidity})
    if uses_c1120 and c1120_any_lt_100:
        checklist.append({"label": "Ignored <100% owned C‑corps", "checked": True})
    if uses_support_income:
        checklist.append({"label": "Court order + proof of receipt + ≥3 years continuance", "checked": st.session_state.support_continuance_ok})
    if not other_df.empty:
        checklist.append({"label": "Evidence of receipt/continuance for other income", "checked": False})
    if not checklist:
        checklist = [{"label": "Standard disclosures", "checked": False}]
    return {
        "incomes": incomes,
        "fees": fees,
        "total_income": total_income,
        "other_debts": other_debts,
        "FE": FE,
        "BE": BE,
        "rule_results": rule_results,
        "blocking": blocking,
        "checklist": checklist,
    }


def render_property_section():
    st.header("Property")
    with st.expander("Payment & Proposed Housing", expanded=True):
        H = st.session_state.housing
        c1, c2, c3 = st.columns(3)
        H["purchase_price"] = c1.number_input("Purchase Price ($)", value=float(H["purchase_price"]), step=1000.0)
        H["down_payment_amt"] = c2.number_input("Down Payment Amount ($)", value=float(H["down_payment_amt"]), step=1000.0)
        H["rate_pct"] = c3.number_input("Interest Rate (%)", value=float(H["rate_pct"]), step=0.125)
        c4, c5, c6 = st.columns(3)
        H["term_years"] = c4.number_input("Term (years)", value=int(H["term_years"]), step=5)
        H["tax_rate_pct"] = c5.number_input("Property Tax Rate (%)", value=float(H["tax_rate_pct"]), step=0.05)
        H["hoi_annual"] = c6.number_input("Homeowners Insurance (Annual $)", value=float(H["hoi_annual"]), step=50.0)
        c7, c8 = st.columns(2)
        H["hoa_monthly"] = c7.number_input("HOA/Condo Dues (Monthly $)", value=float(H["hoa_monthly"]), step=10.0)
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
        st.write(f"**Adjusted Loan (after financed fee if applicable):** ${fees['adjusted_loan']:,.0f}")
        st.write(f"**LTV (base): {fees['ltv']:.2f}%**")
        st.write(
            f"**P&I:** ${fees['pi']:,.2f} | **Taxes:** ${fees['taxes']:,.2f} | **HOI:** ${fees['hoi']:,.2f} | **HOA:** ${fees['hoa']:,.2f} | **MI/MIP/Annual:** ${fees['mi']:,.2f}"
        )
        st.write(f"**Proposed Housing (PITI + HOA + MI): ${fees['total']:,.2f}**")
    with st.expander("MI / MIP / Fees"):
        st.session_state.fico_bucket = st.selectbox(
            "FICO Bucket (display only)",
            [">=740", "720-739", "700-719", "660-699", "620-659", "<620"],
        )
        mi_tab, fha_tab, va_tab, usda_tab = st.tabs(
            [
                "Conventional MI Bands (annual %) by LTV",
                "FHA Factors",
                "VA Funding Fee Table (%)",
                "USDA Guarantee & Annual (%)",
            ]
        )
        with mi_tab:
            mi = st.session_state.program_tables["conventional_mi"]
            remove = []
            for i, (band, pct) in enumerate(list(mi.items())):
                with st.container():
                    st.markdown(f"**Band {i + 1}**")
                    c1, c2, c3 = st.columns([2, 1, 1])
                    new_band = c1.text_input("LTV Band", value=band, key=f"mi_band_{i}")
                    new_pct = c2.number_input(
                        "Annual %", value=float(pct), step=0.01, key=f"mi_pct_{i}"
                    )
                    if c3.button("Remove", key=f"mi_rm_{i}"):
                        remove.append(band)
                    else:
                        if new_band != band:
                            mi.pop(band)
                            mi[new_band] = new_pct
                        else:
                            mi[band] = new_pct
                st.divider()
            for band in remove:
                mi.pop(band, None)
            if st.button("Add LTV Band", key="mi_add"):
                mi[f"Band{len(mi) + 1}"] = 0.0
        with fha_tab:
            cols = st.columns(2)
            st.session_state.program_tables["fha"]["ufmip_pct"] = cols[0].number_input(
                "Upfront MIP (%)",
                value=float(st.session_state.program_tables["fha"].get("ufmip_pct", 1.75)),
                step=0.05,
            )
            tbl = st.session_state.program_tables["fha"].get("annual_table", {})
            remove = []
            for i, (k, v) in enumerate(list(tbl.items())):
                with st.container():
                    st.markdown(f"**Tier {i + 1}**")
                    c1, c2, c3 = st.columns([2, 1, 1])
                    new_k = c1.text_input("Key", value=k, key=f"fha_key_{i}")
                    new_v = c2.number_input(
                        "Annual %", value=float(v), step=0.01, key=f"fha_pct_{i}"
                    )
                    if c3.button("Remove", key=f"fha_rm_{i}"):
                        remove.append(k)
                    else:
                        if new_k != k:
                            tbl.pop(k)
                            tbl[new_k] = new_v
                        else:
                            tbl[k] = new_v
                st.divider()
            for k in remove:
                tbl.pop(k, None)
            if st.button("Add Tier", key="fha_add"):
                tbl[f"key{len(tbl) + 1}"] = 0.0
            st.session_state.program_tables["fha"]["annual_table"] = tbl
        with va_tab:
            st.session_state.first_use_va = st.checkbox("First Use", value=bool(st.session_state.first_use_va))
            va = st.session_state.program_tables["va"]
            remove = []
            for i, (k, v) in enumerate(list(va.items())):
                with st.container():
                    st.markdown(f"**Row {i + 1}**")
                    c1, c2, c3 = st.columns([2, 1, 1])
                    new_k = c1.text_input("Key", value=k, key=f"va_key_{i}")
                    new_v = c2.number_input("Pct", value=float(v), step=0.01, key=f"va_pct_{i}")
                    if c3.button("Remove", key=f"va_rm_{i}"):
                        remove.append(k)
                    else:
                        if new_k != k:
                            va.pop(k)
                            va[new_k] = new_v
                        else:
                            va[k] = new_v
                st.divider()
            for k in remove:
                va.pop(k, None)
            if st.button("Add Row", key="va_add"):
                va[f"key{len(va) + 1}"] = 0.0
        with usda_tab:
            usda = st.session_state.program_tables["usda"]
            c = st.columns(2)
            usda["guarantee_pct"] = c[0].number_input("Guarantee Fee (%)", value=float(usda.get("guarantee_pct", 1.0)), step=0.05)
            usda["annual_pct"] = c[1].number_input("Annual Fee (%)", value=float(usda.get("annual_pct", 0.35)), step=0.05)
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

def render_borrower_setup():
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
            "Number of Borrowers", min_value=1, max_value=4, value=int(st.session_state.num_borrowers), step=1
        )
        for i in range(1, st.session_state.num_borrowers + 1):
            st.session_state.borrower_names[i] = st.text_input(
                f"Borrower {i} name", value=st.session_state.borrower_names.get(i, f"Borrower {i}")
            )

def render_income_section():
    st.header("Income")
    st.session_state.selfemp_year_mode = st.radio(
        "Self-employed income calculation",
        ["Average two years", "Most recent year only"],
        horizontal=True,
        index=0 if st.session_state.selfemp_year_mode == "average" else 1,
    )
    with st.expander("W‑2 / Base Employment"):
        render_w2_form()
    with st.expander("Self‑Employed — Schedule C"):
        render_schedule_c_form()
    with st.expander("K‑1 Income"):
        render_k1_form()
    with st.expander("Regular Corporation — 1120 (100% owner only)"):
        render_corp1120_form()
    with st.expander("Rental Income — Policy"):
        render_rental_form()
    with st.expander("Other Qualifying Income"):
        render_other_income_form()

def render_housing_debts():
    st.header("Debts")
    with st.expander("Other Recurring Debts"):
        render_debt_form()
    st.divider()
    render_property_section()

def render_dashboard():
    data = compute_results()
    incomes = data["incomes"]
    fees = data["fees"]
    total_income = data["total_income"]
    other_debts = data["other_debts"]
    FE = data["FE"]
    BE = data["BE"]
    rule_results = data["rule_results"]
    st.dataframe(incomes, use_container_width=True)
    if not incomes.empty:
        bcols = st.columns(len(incomes))
        for idx, row in enumerate(incomes.itertuples()):
            bcols[idx].metric(
                f"Borrower {row.BorrowerID} Income", f"${row.TotalMonthlyIncome:,.2f}"
            )
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
    st.write("**Documentation Checklist**")
    checklist = data["checklist"]
    for i, item in enumerate(checklist):
        checklist[i]["checked"] = st.checkbox(item["label"], value=item["checked"], key=f"chk_{i}")
    st.session_state["checklist"] = checklist

def render_exports():
    data = compute_results()
    incomes = data["incomes"]
    fees = data["fees"]
    total_income = data["total_income"]
    other_debts = data["other_debts"]
    FE = data["FE"]
    BE = data["BE"]
    rule_results = data["rule_results"]
    blocking = data["blocking"]
    checklist = st.session_state.get("checklist", data["checklist"])
    st.write("**Disclaimer**")
    st.caption(DISCLAIMER)
    st.divider()
    c1, c2, c3 = st.columns([2, 1, 1])
    if blocking:
        st.error("Critical warnings present. Provide an override reason to enable PDF export.")
        st.session_state.override_reason = c1.text_input(
            "Override reason (will be embedded in PDF)", value=st.session_state.override_reason
        )
    else:
        st.session_state.override_reason = ""

    def make_csv_bytes():
        buf = io.StringIO()
        summary = pd.DataFrame([
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
        ])
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
            build_prequal_pdf(
                {
                    "path": path,
                    "branding": branding,
                    "snapshot": snapshot,
                    "rows": rows,
                    "warnings": warn_export,
                    "checklist": checklist,
                }
            )
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
        k1_rows = pd.DataFrame(st.session_state.k1_rows)
        k1_allowed = st.session_state.k1_verified_distributions or st.session_state.k1_analyzed_liquidity
        k1_input = k1_rows if (not k1_rows.empty and k1_allowed) else None
        incomes = combine_income(
            st.session_state.num_borrowers,
            pd.DataFrame(st.session_state.w2_rows),
            pd.DataFrame(st.session_state.schc_rows),
            k1_input,
            pd.DataFrame(st.session_state.c1120_rows),
            rentals_policy(
                pd.DataFrame(st.session_state.rental_rows),
                st.session_state.rental_method,
                st.session_state.subject_market_rent,
            ),
            pd.DataFrame(st.session_state.other_rows),
            recent_selfemp=st.session_state.selfemp_year_mode != "average",
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

init_state()

if "theme" not in st.session_state:
    st.session_state.theme = "light"
dark_on = st.sidebar.toggle("Dark mode", value=st.session_state.theme == "dark")
st.session_state.theme = "dark" if dark_on else "light"
if st.session_state.theme == "dark":
    st.markdown(
        """
        <style>
        [data-testid=\"stAppViewContainer\"]{background-color:#0e1117;color:#fafafa;}
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        [data-testid=\"stAppViewContainer\"]{background-color:#ffffff;color:#000000;}
        </style>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <style>
    @media (max-width: 600px) {
        div[class^='stColumn'] {flex: 1 1 100% !important;}
    }
    input, select {width: 100% !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

steps = ["Borrower Setup", "Income", "Housing/Debts", "Dashboard", "Exports"]
completed = {
    "Borrower Setup": True,
    "Income": bool(
        st.session_state.w2_rows
        or st.session_state.schc_rows
        or st.session_state.k1_rows
        or st.session_state.c1120_rows
        or st.session_state.rental_rows
        or st.session_state.other_rows
    ),
    "Housing/Debts": bool(st.session_state.debt_rows) or bool(st.session_state.housing),
    "Dashboard": False,
    "Exports": False,
}
nav = st.sidebar.radio(
    "Navigate",
    steps,
    format_func=lambda x: ("✅ " if completed.get(x) else "") + x,
)

st.title("AMALO MORTGAGE INCOME & DTI DASHBOARD")
st.caption("Florida-friendly defaults • Program-aware calculations • Guardrails & warnings • Exports")

if nav == "Borrower Setup":
    render_borrower_setup()
elif nav == "Income":
    render_income_section()
elif nav == "Housing/Debts":
    render_housing_debts()
elif nav == "Dashboard":
    render_dashboard()
elif nav == "Exports":
    render_exports()
