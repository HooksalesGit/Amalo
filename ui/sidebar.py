import json
import streamlit as st
from core.presets import CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE
from core.state import save_session_state


def render_fee_sidebar():
    """Sidebar with editable MI/MIP/funding fee tables."""
    st.session_state.setdefault("conv_mi_table", CONV_MI_BANDS)
    st.session_state.setdefault("fha_table", FHA_TABLES)
    st.session_state.setdefault("va_table", VA_TABLE)
    st.session_state.setdefault("usda_table", USDA_TABLE)

    st.sidebar.header("MI / MIP / Guarantee")
    conv_json = st.sidebar.text_area(
        "Conventional MI Table",
        value=json.dumps(st.session_state["conv_mi_table"], indent=2),
    )
    fha_json = st.sidebar.text_area(
        "FHA MIP Table",
        value=json.dumps(st.session_state["fha_table"], indent=2),
    )
    va_json = st.sidebar.text_area(
        "VA Funding Fee Table",
        value=json.dumps(st.session_state["va_table"], indent=2),
    )
    usda_json = st.sidebar.text_area(
        "USDA Guarantee Fee Table",
        value=json.dumps(st.session_state["usda_table"], indent=2),
    )

    try:
        st.session_state["conv_mi_table"] = json.loads(conv_json)
    except Exception:
        pass
    try:
        st.session_state["fha_table"] = json.loads(fha_json)
    except Exception:
        pass
    try:
        st.session_state["va_table"] = json.loads(va_json)
    except Exception:
        pass
    try:
        st.session_state["usda_table"] = json.loads(usda_json)
    except Exception:
        pass
    save_session_state()
