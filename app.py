import streamlit as st
from core.presets import (
    PROGRAM_PRESETS,
    CONV_MI_BANDS,
    FHA_TABLES,
    VA_TABLE,
    USDA_TABLE,
)
from core.calculators import piti_components, dti, monthly_payment
from core.models import W2
from ui.topbar import render_topbar
from ui.cards_income import render_income_cards
from ui.cards_debts import render_debt_cards
from ui.bottombar import render_bottombar


# ---------------------------------------------------------------------------
# Minimal W-2 form kept for test coverage
# ---------------------------------------------------------------------------

def render_w2_form():
    st.session_state.setdefault("w2_rows", [])
    if st.button("Add W2 Job", key="add_w2_job"):
        st.session_state.w2_rows.append(W2().model_dump())
    for idx, row in enumerate(st.session_state.w2_rows):
        with st.expander(f"W2 #{idx+1}"):
            for field, val in row.items():
                st.text_input(field, value=str(val), key=f"w2_{idx}_{field}")


# ---------------------------------------------------------------------------
# Property / housing helpers
# ---------------------------------------------------------------------------

def render_property_column():
    st.session_state.setdefault("housing", {})
    h = st.session_state.housing
    with st.expander("Payment & Housing"):
        h["purchase_price"] = st.number_input("Purchase Price", value=float(h.get("purchase_price", 0.0)))
        h["down_payment_amt"] = st.number_input("Down Payment", value=float(h.get("down_payment_amt", 0.0)))
        h["rate_pct"] = st.number_input("Rate %", value=float(h.get("rate_pct", 0.0)))
        h["term_years"] = st.number_input("Term (years)", value=float(h.get("term_years", 30)))
        base_loan = h.get("purchase_price", 0.0) - h.get("down_payment_amt", 0.0)
        pi_only = monthly_payment(
            base_loan,
            h.get("rate_pct", 0.0),
            h.get("term_years", 30),
        )
        st.caption(f"Monthly P&I: ${pi_only:,.2f}")
        h["tax_rate_pct"] = st.number_input(
            "Tax Rate %",
            value=float(h.get("tax_rate_pct", 0.0)),
            help="Avg Florida property tax ~1% of purchase price",
        )
        h["hoi_rate_pct"] = st.number_input(
            "HOI Rate %",
            value=float(h.get("hoi_rate_pct", 0.0)),
            help="Enter as % of purchase price (FL avg ~1%)",
        )
        h["hoi_annual"] = st.number_input(
            "HOI Annual",
            value=float(h.get("hoi_annual", 0.0)),
            help="Annual homeowners insurance amount",
        )
        if h.get("hoi_rate_pct", 0.0) > 0:
            h["hoi_annual"] = h.get("purchase_price", 0.0) * h["hoi_rate_pct"] / 100
            st.caption(f"Calculated HOI Annual: ${h['hoi_annual']:,.2f}")
        h["hoa_monthly"] = st.number_input(
            "HOA Monthly",
            value=float(h.get("hoa_monthly", 0.0)),
            help="Florida HOA averages ~$250/mo",
        )
        h["finance_upfront"] = st.checkbox("Finance Upfront Fees", value=bool(h.get("finance_upfront", True)))
    base_loan = h.get("purchase_price", 0.0) - h.get("down_payment_amt", 0.0)
    comps = piti_components(
        st.session_state.get("program_name", "Conventional"),
        h.get("purchase_price", 0.0),
        base_loan,
        h.get("rate_pct", 0.0),
        h.get("term_years", 30),
        h.get("tax_rate_pct", 0.0),
        h.get("hoi_annual", 0.0),
        h.get("hoa_monthly", 0.0),
        CONV_MI_BANDS,
        FHA_TABLES,
        VA_TABLE,
        USDA_TABLE,
        h.get("finance_upfront", True),
        True,
        None,
    )
    st.session_state["housing_calc"] = comps
    st.caption(f"Base Loan: ${base_loan:,.0f} • LTV: {comps['ltv']*100:.2f}%")
    st.caption(f"PITIA: ${comps['total']:,.2f}")
    return comps


# ---------------------------------------------------------------------------
# Dashboard view
# ---------------------------------------------------------------------------

def render_dashboard_view(summary):
    st.header("Dashboard")
    cols = st.columns(4)
    cols[0].metric("Total Income", f"${summary['total_income']:,.2f}")
    cols[1].metric("PITIA", f"${summary['pitia']:,.2f}")
    cols[2].metric("FE DTI", f"{summary['fe_dti']*100:.2f}%")
    cols[3].metric("BE DTI", f"{summary['be_dti']*100:.2f}%")
    from core.rules import evaluate_rules

    state = {
        "total_income": summary["total_income"],
        "FE": summary["fe_dti"],
        "BE": summary["be_dti"],
        "target_FE": st.session_state["program_targets"]["fe_target"],
        "target_BE": st.session_state["program_targets"]["be_target"],
    }
    for r in evaluate_rules(state):
        if r.severity == "critical":
            st.error(f"[{r.code}] {r.message}")
        elif r.severity == "warn":
            st.warning(f"[{r.code}] {r.message}")
        else:
            st.info(f"[{r.code}] {r.message}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(layout="wide")
    st.session_state.setdefault("view_mode", "data_entry")
    st.session_state.setdefault(
        "program_targets",
        {
            "fe_target": PROGRAM_PRESETS["Conventional"]["FE"],
            "be_target": PROGRAM_PRESETS["Conventional"]["BE"],
        },
    )
    st.session_state.setdefault("ui_prefs", {"show_bottom_bar": False, "language": "en"})

    # Render the top bar and capture current program/target selections. The
    # selectbox in ``render_topbar`` already manages ``program_name`` via
    # Streamlit's ``session_state``. Attempting to assign to the same key again
    # triggers a ``StreamlitAPIException`` in recent versions of Streamlit.
    # Rely on the widget-managed value instead of overwriting it here.
    view_mode, targets, _program = render_topbar()
    st.session_state["program_targets"] = targets
    if view_mode == "data_entry":
        cols = st.columns(3)
        with cols[0]:
            income_total = render_income_cards()
        with cols[1]:
            debt_total = render_debt_cards()
        with cols[2]:
            housing = render_property_column()
        fe, be = dti(housing["total"], housing["total"] + debt_total, income_total)
        summary = {
            "total_income": income_total,
            "pitia": housing["total"],
            "fe_dti": fe,
            "be_dti": be,
            "fe_target": targets["fe_target"],
            "be_target": targets["be_target"],
        }
        render_bottombar(summary, st.session_state["ui_prefs"].get("show_bottom_bar", False))
    else:
        housing = st.session_state.get("housing_calc", {"total": 0})
        income_total = sum(
            card.get("payload", {}).get("QualMonthly", card.get("payload", {}).get("GrossMonthly", 0))
            or 0
            for card in st.session_state.get("income_cards", [])
        )
        debt_total = sum(
            card.get("payload", {}).get("monthly_payment", 0) or 0
            for card in st.session_state.get("debt_cards", [])
        )
        fe, be = dti(housing.get("total", 0), housing.get("total", 0) + debt_total, income_total)
        summary = {
            "total_income": income_total,
            "pitia": housing.get("total", 0),
            "fe_dti": fe,
            "be_dti": be,
            "fe_target": st.session_state["program_targets"]["fe_target"],
            "be_target": st.session_state["program_targets"]["be_target"],
        }
        render_dashboard_view(summary)

    st.sidebar.checkbox(
        "Show Bottom Bar",
        key="show_bottom_bar",
        value=st.session_state["ui_prefs"].get("show_bottom_bar", False),
    )
    st.session_state["ui_prefs"]["show_bottom_bar"] = st.session_state["show_bottom_bar"]

    st.markdown(
        """
        <script>
        document.addEventListener('keydown', function(e){
            if (e.key === 'a') {
                const btn = Array.from(parent.document.querySelectorAll('button')).find(b => b.innerText === 'Add Income Card');
                if (btn) btn.click();
            }
            if (e.key === 'd') {
                const btn = Array.from(parent.document.querySelectorAll('button')).find(b => b.innerText === 'Add Debt Card');
                if (btn) btn.click();
            }
        });
        </script>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
