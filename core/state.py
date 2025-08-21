import json
from pathlib import Path
import streamlit as st

STATE_FILE = Path("session_state.json")


def load_session_state(path: Path = STATE_FILE):
    """Load session state from a JSON file if present."""
    if path.exists():
        try:
            data = json.loads(path.read_text())
            for k, v in data.items():
                if k not in st.session_state:
                    st.session_state[k] = v
        except Exception:
            pass


def save_session_state(path: Path = STATE_FILE):
    """Persist the current session state to disk."""
    try:
        path.write_text(json.dumps({k: v for k, v in st.session_state.items()}))
    except Exception:
        pass
