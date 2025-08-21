import streamlit as st
from core.presets import PROGRAM_PRESETS
from core.i18n import t
from core.version import __version__


def render_topbar():
    """Render the sticky top bar and return view mode, targets and program."""
    st.markdown(
        """
        <style>
        .amalo-topbar {position:sticky; top:0; background-color:white; z-index:100; padding:4px 8px; border-bottom:1px solid #ddd;}
        .amalo-topbar div[data-testid="stHorizontalBlock"] {align-items:center;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container():
        st.markdown('<div class="amalo-topbar">', unsafe_allow_html=True)
        left, center, right = st.columns([1, 2, 1])
        lang = st.session_state.get("ui_prefs", {}).get("language", "en")
        with left:
            st.markdown(f"**AMALO v{__version__}**")
        with center:
            program = st.selectbox(
                t("Program", lang), list(PROGRAM_PRESETS.keys()), key="program_name"
            )
            tgt = st.session_state.get(
                "program_targets",
                {
                    "fe_target": PROGRAM_PRESETS[program]["FE"],
                    "be_target": PROGRAM_PRESETS[program]["BE"],
                },
            )
            c1, c2, c3 = st.columns([1, 1, 1])
            fe = c1.number_input(
                "FE Target",
                value=float(tgt.get("fe_target", PROGRAM_PRESETS[program]["FE"])),
                key="fe_target",
            )
            be = c2.number_input(
                "BE Target",
                value=float(tgt.get("be_target", PROGRAM_PRESETS[program]["BE"])),
                key="be_target",
            )
            if c3.button("Apply Presets"):
                fe = PROGRAM_PRESETS[program]["FE"]
                be = PROGRAM_PRESETS[program]["BE"]
                st.session_state["fe_target"] = fe
                st.session_state["be_target"] = be
            tgt = {"fe_target": fe, "be_target": be}
        with right:
            view_mode = st.radio(
                t("View", lang),
                ["data_entry", "dashboard", "max_qualifiers"],
                horizontal=True,
                key="view_mode",
            )
            st.session_state.setdefault("ui_prefs", {})
            st.session_state["ui_prefs"].setdefault("language", "en")
            st.session_state["ui_prefs"]["language"] = st.selectbox(
                t("Lang", lang),
                ["en", "es"],
                key="ui_lang",
                index=["en", "es"].index(
                    st.session_state["ui_prefs"].get("language", "en")
                ),
            )
        st.markdown("</div>", unsafe_allow_html=True)
    st.session_state["program_targets"] = tgt
    return view_mode, tgt, program
