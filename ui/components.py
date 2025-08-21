import json
from pathlib import Path
import streamlit as st

_i18n_cache = {}

def _load_lang(lang: str):
    if lang in _i18n_cache:
        return _i18n_cache[lang]
    path = Path(__file__).parent / "i18n" / f"{lang}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            _i18n_cache[lang] = json.load(f)
    else:
        _i18n_cache[lang] = {}
    return _i18n_cache[lang]

def t(key: str) -> str:
    """Translate a key based on current language preference."""
    lang = st.session_state.get("ui_prefs", {}).get("language", "en")
    table = _load_lang(lang)
    return table.get(key, key)
