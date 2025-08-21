import streamlit as st
from core.calculators import dti, max_qualifying_loan, what_if_max_qualifying
from core.presets import CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE
from app import fico_to_bucket


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
    fe, be = dti(
        res["max_pi"] + tax_ins, res["max_pi"] + tax_ins + other_debts, tot_inc
    )
    st.caption(
        f"Base Loan: ${res['base_loan']:,.0f} • Adjusted Loan: ${res['adjusted_loan']:,.0f} • Purchase Price: ${res['purchase_price']:,.0f}"
    )
    st.caption(f"FE DTI: {fe*100:.2f}% • BE DTI: {be*100:.2f}%")

    c1, c2, c3 = st.columns(3)
    with c1:
        more_down = st.checkbox("Increase down payment by $10k", key="mq_more_down")
    with c2:
        more_rate = st.checkbox("Increase rate by 0.25%", key="mq_more_rate")
    with c3:
        more_debt = st.checkbox("Add $300 monthly debt", key="mq_more_debt")

    if more_down or more_rate or more_debt:
        scenarios = what_if_max_qualifying(
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
        key = "base"
        if more_down:
            key = "down_payment_plus_10k"
        if more_rate:
            key = "rate_plus_0.25"
        if more_debt:
            key = "debt_plus_300"
        alt = scenarios[key]
        st.caption(
            f"What-If Max Loan: ${alt['max_loan']:,.0f} • FE DTI: {alt['fe_dti']*100:.2f}% • BE DTI: {alt['be_dti']*100:.2f}%"
        )
