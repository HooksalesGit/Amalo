"""UI helpers for documentation checklist."""
from __future__ import annotations
import re
import streamlit as st
from core.checklist import build_document_checklist


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def render_document_checklist():
    """Render an auto-generated checklist based on income cards."""
    docs = build_document_checklist(st.session_state.get("income_cards", []))
    st.session_state.setdefault("doc_checklist_state", {})
    with st.expander("Documentation Checklist"):
        for doc in docs:
            key = _slug(doc)
            checked = st.session_state["doc_checklist_state"].get(doc, False)
            st.session_state["doc_checklist_state"][doc] = st.checkbox(doc, value=checked, key=f"doc_{key}")
    st.session_state["doc_checklist"] = [
        {"label": doc, "checked": st.session_state["doc_checklist_state"].get(doc, False)}
        for doc in docs
    ]
