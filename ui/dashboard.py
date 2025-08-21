import streamlit as st
from core.rules import evaluate_rules


def render_dashboard_view(summary):
    """Render dashboard metrics and rule evaluations."""
    st.header("Dashboard")
    cols = st.columns(4)
    cols[0].metric("Total Income", f"${summary['total_income']:,.2f}")
    cols[1].metric("PITIA", f"${summary['pitia']:,.2f}")
    cols[2].metric("FE DTI", f"{summary['fe_dti']*100:.2f}%")
    cols[3].metric("BE DTI", f"{summary['be_dti']*100:.2f}%")

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
