import json
import os
from typing import Any

import streamlit as st

SESSION_FILE = "session_data.json"


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
            st.session_state.setdefault(key, val)
    except Exception:
        pass


def save_state() -> None:
    """Persist serializable session state to ``SESSION_FILE``."""
    try:
        data = {k: v for k, v in st.session_state.items() if _serializable(v)}
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
