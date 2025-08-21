"""Document checklist helpers."""
from __future__ import annotations
from typing import List, Dict

# Mapping of income card types to required documents
DOCS_BY_TYPE: Dict[str, List[str]] = {
    "w2": ["Last two pay stubs", "W-2s"],
    "schc": ["1040s", "Business bank statements"],
    "k1": ["1040s", "K-1s"],
    "c1120": ["1040s", "Business bank statements"],
    "rental": ["1040s", "Leases"],
}


def _docs_for_other(payload: Dict) -> List[str]:
    t = str(payload.get("Type", "")).lower()
    if "child" in t:
        return ["Child support court orders"]
    return ["Proof of other income"]


def _docs_for_card(card: Dict) -> List[str]:
    t = card.get("type")
    if t == "other":
        return _docs_for_other(card.get("payload", {}))
    return DOCS_BY_TYPE.get(t, [])


def build_document_checklist(income_cards: List[Dict]) -> List[str]:
    """Return a de-duplicated list of required documents."""
    docs: List[str] = []
    for card in income_cards:
        for doc in _docs_for_card(card):
            if doc not in docs:
                docs.append(doc)
    return docs
