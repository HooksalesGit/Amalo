import streamlit as st


def render_bottombar(summary: dict, enabled: bool):
    if not enabled:
        return
    st.markdown(
        """
        <style>
        .amalo-bottombar {position:fixed; bottom:0; left:0; right:0; background-color:white; border-top:1px solid #ddd; padding:4px 8px; z-index:100;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container():
        st.markdown('<div class="amalo-bottombar">', unsafe_allow_html=True)
        cols = st.columns([1,1,1,1,1,1])
        cols[0].metric("Total Income", f"${summary.get('total_income',0):,.2f}")
        cols[1].metric("PITIA", f"${summary.get('pitia',0):,.2f}")
        fe = summary.get("fe_dti", 0.0)
        fe_target = summary.get("fe_target", 0.0)
        cols[2].metric("FE DTI", f"{fe*100:.2f}%", delta="PASS" if fe*100 <= fe_target else "CHECK")
        be = summary.get("be_dti", 0.0)
        be_target = summary.get("be_target", 0.0)
        cols[3].metric("BE DTI", f"{be*100:.2f}%", delta="PASS" if be*100 <= be_target else "CHECK")
        if cols[4].button("Open Dashboard"):
            st.session_state["view_mode"] = "dashboard"
            st.experimental_rerun()
        cols[5].button("Open Max Qualifiers")
        st.markdown("</div>", unsafe_allow_html=True)
