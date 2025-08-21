"""PDF export stub."""
from __future__ import annotations
from typing import Any, Dict

from core.presets import DISCLAIMER


def build_prequal_pdf(data: Dict[str, Any]) -> bytes:
    """Build a prequalification PDF from provided data.

    This stub encodes the documentation checklist into a plain text payload with
    simple checkboxes. A real PDF implementation will replace this later.
    """
    checklist = data.get("checklist", [])
    lines = ["Documentation Checklist:"]
    for item in checklist:
        box = "[x]" if item.get("checked") else "[ ]"
        lines.append(f"{box} {item.get('label', '')}")
    return "\n".join(lines).encode()
