import streamlit as st
from core.calculators import max_qualifying_loan
from core.presets import CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE
from core.utils import fico_to_bucket


def render_max_qualifiers_view():
    """Render the max qualifiers solver interface."""
    st.header("Max Qualifiers")
    tot_inc = st.number_input("Total Monthly Income", value=0.0, key="mq_inc")
    other_debts = st.number_input("Other Monthly Debts", value=0.0, key="mq_debts")
    tax_ins = st.number_input("Taxes/Ins/HOA/MI", value=0.0, key="mq_ti")
    rate = st.number_input("Rate %", value=0.0, key="mq_rate")
    term = st.number_input("Term (years)", value=30.0, key="mq_term")
    down = st.number_input("Down Payment", value=0.0, key="mq_down")
    program = st.session_state.get("program_name", "Conventional")
    targets = st.session_state.get(
        "program_targets", {"fe_target": 0.0, "be_target": 0.0}
    )
    res = max_qualifying_loan(
        tot_inc,
        other_debts,
        tax_ins,
        targets.get("fe_target", 0.0),
        targets.get("be_target", 0.0),
        rate,
        term,
        down,
        program,
        st.session_state.get("conv_mi_table", CONV_MI_BANDS),
        st.session_state.get("fha_table", FHA_TABLES),
        st.session_state.get("va_table", VA_TABLE),
        st.session_state.get("usda_table", USDA_TABLE),
        True,
        True,
        fico_to_bucket(st.session_state.get("housing", {}).get("credit_score")),
    )
    st.caption(
        f"Base Loan: ${res['base_loan']:,.0f} • Adjusted Loan: ${res['adjusted_loan']:,.0f} • Purchase Price: ${res['purchase_price']:,.0f}"
    )
