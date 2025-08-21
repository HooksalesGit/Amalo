import streamlit as st
from core.calculators import piti_components, monthly_payment
from core.presets import CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE
from core.models import Housing


def fico_to_bucket(score):
    """Map a numeric credit score to the preset FICO buckets."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "760+"
    if s >= 760:
        return "760+"
    if s >= 720:
        return "720-759"
    return "<720"


def render_property_column():
    st.session_state.setdefault("housing", {})
    h = st.session_state.housing
    with st.expander("Payment & Housing"):
        h["purchase_price"] = st.number_input(
            "Purchase Price", value=float(h.get("purchase_price", 0.0))
        )
        h["down_payment_amt"] = st.number_input(
            "Down Payment", value=float(h.get("down_payment_amt", 0.0))
        )
        h["rate_pct"] = st.number_input("Rate %", value=float(h.get("rate_pct", 0.0)))
        h["term_years"] = st.number_input(
            "Term (years)", value=float(h.get("term_years", 30))
        )
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
        h["finance_upfront"] = st.checkbox(
            "Finance Upfront Fees", value=bool(h.get("finance_upfront", True))
        )
        h["credit_score"] = st.number_input(
            "Credit Score", value=float(h.get("credit_score", 760))
        )
        h["first_use_va"] = st.checkbox(
            "First Use VA", value=bool(h.get("first_use_va", True))
        )
    # validate inputs via Pydantic
    h_model = Housing(**h)
    h = h_model.model_dump()
    st.session_state.housing = h
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
        st.session_state.get("conv_mi_table", CONV_MI_BANDS),
        st.session_state.get("fha_table", FHA_TABLES),
        st.session_state.get("va_table", VA_TABLE),
        st.session_state.get("usda_table", USDA_TABLE),
        h.get("finance_upfront", True),
        h.get("first_use_va", True),
        fico_to_bucket(h.get("credit_score")),
    )
    st.session_state["housing_calc"] = comps
    program = st.session_state.get("program_name", "Conventional")
    if h.get("finance_upfront", True) and program in ("FHA", "VA", "USDA"):
        st.caption(
            f"Base Loan: ${base_loan:,.0f} • Adjusted Loan: ${comps['adjusted_loan']:,.0f}"
        )
    else:
        st.caption(f"Base Loan: ${base_loan:,.0f}")
    st.caption(f"LTV: {comps['ltv']*100:.2f}%")
    st.caption(f"PITIA: ${comps['total']:,.2f}")
    return comps
