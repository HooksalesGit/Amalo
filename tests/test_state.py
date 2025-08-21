import json
import streamlit as st
from core import state


def test_save_state_ignores_widget_keys(tmp_path, monkeypatch):
    file = tmp_path / "session.json"
    monkeypatch.setattr(state, "SESSION_FILE", str(file))
    st.session_state.clear()
    st.session_state["income_cards"] = []
    st.session_state["add_income_card"] = True
    state.save_state()
    data = json.loads(file.read_text())
    assert "add_income_card" not in data
    assert "income_cards" in data


def test_load_state_ignores_widget_keys(tmp_path, monkeypatch):
    file = tmp_path / "session.json"
    file.write_text(json.dumps({"income_cards": [], "add_income_card": True}))
    monkeypatch.setattr(state, "SESSION_FILE", str(file))
    st.session_state.clear()
    state.load_state()
    assert "income_cards" in st.session_state
    assert "add_income_card" not in st.session_state
