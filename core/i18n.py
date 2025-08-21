"""Minimal internationalization helpers."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

TRANSLATIONS_DIR = Path(__file__).resolve().parents[1] / "translations"


@lru_cache()
def load_translations(lang: str) -> Dict[str, str]:
    """Load translation mappings for the given language."""
    path = TRANSLATIONS_DIR / f"{lang}.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def t(key: str, lang: str) -> str:
    """Translate ``key`` using the specified language."""
    return load_translations(lang).get(key, key)
