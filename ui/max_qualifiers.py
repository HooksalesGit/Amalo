import streamlit as st
from core.calculators import compare_scenarios, dti, max_qualifying_loan
from core.presets import (
    CONV_MI_BANDS,
    FHA_TABLES,
    VA_TABLE,
    USDA_TABLE,
    PROGRAM_PRESETS,
)
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

    if st.checkbox("Compare alternate scenario", key="mq_compare"):
        alt_rate = st.number_input("Alt Rate %", value=rate, key="mq_alt_rate")
        alt_down = st.number_input("Alt Down Payment", value=down, key="mq_alt_down")
        alt_program = st.selectbox(
            "Alt Program",
            list(PROGRAM_PRESETS.keys()),
            index=list(PROGRAM_PRESETS.keys()).index(program),
            key="mq_alt_program",
        )
        scenarios = compare_scenarios(
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
            alt_rate_pct=alt_rate,
            alt_down_payment_amt=alt_down,
            alt_program=alt_program,
        )
        c1, c2 = st.columns(2)
        c1.caption(
            f"Base Max Purchase: ${scenarios['base']['max_purchase']:,.0f} • FE DTI: {scenarios['base']['fe_dti']*100:.2f}% • BE DTI: {scenarios['base']['be_dti']*100:.2f}%"
        )
        c2.caption(
            f"Alt Max Purchase: ${scenarios['alt']['max_purchase']:,.0f} • FE DTI: {scenarios['alt']['fe_dti']*100:.2f}% • BE DTI: {scenarios['alt']['be_dti']*100:.2f}%"
        )
