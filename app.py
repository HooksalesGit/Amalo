import streamlit as st

from core.presets import PROGRAM_PRESETS
from core.calculators import dti
from core.state import load_session_state, save_session_state
from ui.topbar import render_topbar
from ui.cards_income import render_income_cards
from ui.cards_debts import render_debt_cards
from ui.bottombar import render_bottombar
from ui.documents import render_document_checklist
from ui.forms import render_w2_form, render_property_column
from ui.sidebar import render_fee_sidebar
from ui.dashboard import render_dashboard_view
from ui.max_qualifiers import render_max_qualifiers_view

# Re-export common rendering helpers for tests
__all__ = [
    "render_w2_form",
    "render_property_column",
    "render_fee_sidebar",
    "render_dashboard_view",
]


load_session_state()


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
    st.session_state.setdefault(
        "ui_prefs", {"show_bottom_bar": False, "language": "en"}
    )
    render_fee_sidebar()

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
            render_document_checklist()
        fe, be = dti(housing["total"], housing["total"] + debt_total, income_total)
        summary = {
            "total_income": income_total,
            "pitia": housing["total"],
            "fe_dti": fe,
            "be_dti": be,
            "fe_target": targets["fe_target"],
            "be_target": targets["be_target"],
        }
        render_bottombar(
            summary, st.session_state["ui_prefs"].get("show_bottom_bar", False)
        )
    elif view_mode == "dashboard":
        housing = st.session_state.get("housing_calc", {"total": 0})
        income_total = sum(
            card.get("payload", {}).get(
                "QualMonthly", card.get("payload", {}).get("GrossMonthly", 0)
            )
            or 0
            for card in st.session_state.get("income_cards", [])
        )
        debt_total = sum(
            card.get("payload", {}).get("monthly_payment", 0) or 0
            for card in st.session_state.get("debt_cards", [])
            if not card.get("payload", {}).get("payoff_at_close", False)
        )
        fe, be = dti(
            housing.get("total", 0), housing.get("total", 0) + debt_total, income_total
        )
        summary = {
            "total_income": income_total,
            "pitia": housing.get("total", 0),
            "fe_dti": fe,
            "be_dti": be,
            "fe_target": st.session_state["program_targets"]["fe_target"],
            "be_target": st.session_state["program_targets"]["be_target"],
        }
        render_dashboard_view(summary)
    else:
        render_max_qualifiers_view()

    st.sidebar.checkbox(
        "Show Bottom Bar",
        key="show_bottom_bar",
        value=st.session_state["ui_prefs"].get("show_bottom_bar", False),
    )
    st.session_state["ui_prefs"]["show_bottom_bar"] = st.session_state[
        "show_bottom_bar"
    ]

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
    save_session_state()


if __name__ == "__main__":
    main()
