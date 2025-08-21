import json
import os
from typing import Any

import streamlit as st

SESSION_FILE = "session_data.json"

# Only persist a curated subset of ``st.session_state`` keys. Streamlit
# widgets such as buttons inject their own keys (e.g. ``add_income_card``)
# into ``session_state`` when interacted with. Persisting those ephemeral
# keys causes ``StreamlitAPIException`` on the next run because widgets with
# the same keys disallow manual assignment. To avoid this, limit persistence
# to known application data keys.
PERSISTED_KEYS = {
    "view_mode",
    "program_name",
    "program_targets",
    "ui_prefs",
    "housing",
    "housing_calc",
    "income_cards",
    "debt_cards",
    "doc_checklist_state",
    "doc_checklist",
    "conv_mi_table",
    "fha_table",
    "va_table",
    "usda_table",
    "w2_rows",
}


def _serializable(value: Any) -> bool:
    return isinstance(value, (int, float, str, bool, list, dict))


def load_state() -> None:
    """Restore Streamlit session state from ``SESSION_FILE`` if it exists."""
    if not os.path.exists(SESSION_FILE):
        return
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, val in data.items():
            if key in PERSISTED_KEYS:
                st.session_state.setdefault(key, val)
    except Exception:
        pass


def save_state() -> None:
    """Persist serializable session state to ``SESSION_FILE``."""
    try:
        data = {
            k: v
            for k, v in st.session_state.items()
            if k in PERSISTED_KEYS and _serializable(v)
        }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
