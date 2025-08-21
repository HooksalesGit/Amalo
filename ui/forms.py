import streamlit as st
from core.models import W2, Housing
from core.calculators import piti_components, monthly_payment
from core.presets import CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE
from core.utils import fico_to_bucket
from core.state import save_session_state


def render_w2_form():
    """Minimal W‑2 form kept for test coverage."""
    st.session_state.setdefault("w2_rows", [])
    if st.button("Add W2 Job", key="add_w2_job"):
        st.session_state.w2_rows.append(W2().model_dump())
        save_session_state()
    for idx, row in enumerate(st.session_state.w2_rows):
        with st.expander(f"W2 #{idx+1}"):
            items = list(row.items())
            for i in range(0, len(items), 2):
                cols = st.columns(2)
                for col_idx, (field, val) in enumerate(items[i : i + 2]):
                    with cols[col_idx]:
                        st.markdown(f"**{field}**")
                        st.caption(f"Enter {field}")
                        st.text_input("", value=str(val), key=f"w2_{idx}_{field}")
    save_session_state()


def render_property_column():
    """Property and housing inputs with Pydantic validation."""
    st.session_state.setdefault("housing", Housing().model_dump())
    h = Housing(**st.session_state["housing"])
    with st.expander("Payment & Housing"):
        h.purchase_price = st.number_input("Purchase Price", value=h.purchase_price)
        h.down_payment_amt = st.number_input("Down Payment", value=h.down_payment_amt)
        h.rate_pct = st.number_input("Rate %", value=h.rate_pct)
        h.term_years = st.number_input("Term (years)", value=h.term_years)
        base_loan = h.purchase_price - h.down_payment_amt
        pi_only = monthly_payment(base_loan, h.rate_pct, h.term_years)
        st.caption(f"Monthly P&I: ${pi_only:,.2f}")
        h.tax_rate_pct = st.number_input(
            "Tax Rate %",
            value=h.tax_rate_pct,
            help="Avg Florida property tax ~1% of purchase price",
        )
        h.hoi_rate_pct = st.number_input(
            "HOI Rate %",
            value=h.hoi_rate_pct,
            help="Enter as % of purchase price (FL avg ~1%)",
        )
        h.hoi_annual = st.number_input(
            "HOI Annual",
            value=h.hoi_annual,
            help="Annual homeowners insurance amount",
        )
        if h.hoi_rate_pct > 0:
            h.hoi_annual = h.purchase_price * h.hoi_rate_pct / 100
            st.caption(f"Calculated HOI Annual: ${h.hoi_annual:,.2f}")
        h.hoa_monthly = st.number_input(
            "HOA Monthly",
            value=h.hoa_monthly,
            help="Florida HOA averages ~$250/mo",
        )
        h.finance_upfront = st.checkbox("Finance Upfront Fees", value=h.finance_upfront)
        h.credit_score = st.number_input("Credit Score", value=h.credit_score)
        h.first_use_va = st.checkbox("First Use VA", value=h.first_use_va)
    st.session_state["housing"] = h.model_dump()
    base_loan = h.purchase_price - h.down_payment_amt
    comps = piti_components(
        st.session_state.get("program_name", "Conventional"),
        h.purchase_price,
        base_loan,
        h.rate_pct,
        h.term_years,
        h.tax_rate_pct,
        h.hoi_annual,
        h.hoa_monthly,
        st.session_state.get("conv_mi_table", CONV_MI_BANDS),
        st.session_state.get("fha_table", FHA_TABLES),
        st.session_state.get("va_table", VA_TABLE),
        st.session_state.get("usda_table", USDA_TABLE),
        h.finance_upfront,
        h.first_use_va,
        fico_to_bucket(h.credit_score),
    )
    st.session_state["housing_calc"] = comps
    program = st.session_state.get("program_name", "Conventional")
    if h.finance_upfront and program in ("FHA", "VA", "USDA"):
        st.caption(
            f"Base Loan: ${base_loan:,.0f} • Adjusted Loan: ${comps['adjusted_loan']:,.0f}"
        )
    else:
        st.caption(f"Base Loan: ${base_loan:,.0f}")
    st.caption(f"LTV: {comps['ltv']*100:.2f}%")
    st.caption(f"PITIA: ${comps['total']:,.2f}")
    save_session_state()
    return comps
