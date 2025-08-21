"""PDF export stub."""
from __future__ import annotations
from typing import Any, Dict

from core.presets import DISCLAIMER


def build_prequal_pdf(data: Dict[str, Any]) -> bytes:
    """Build a prequalification PDF from provided data.

    This stub encodes the documentation checklist into a plain text payload with
    simple checkboxes. A real PDF implementation will replace this later. If
    critical warnings are present an ``override_reason`` is required and recorded
    for audit purposes.
    """

    warnings = data.get("warnings", [])
    if any(w.get("severity") == "critical" for w in warnings):
        override_reason = data.get("override_reason")
        if not override_reason:
            raise ValueError("override_reason required when critical warnings exist")
    else:
        override_reason = data.get("override_reason")

    checklist = data.get("checklist", [])
    lines = ["Documentation Checklist:"]
    for item in checklist:
        box = "[x]" if item.get("checked") else "[ ]"
        lines.append(f"{box} {item.get('label', '')}")

    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"{w.get('severity','')}: {w.get('message','')}")

    if override_reason:
        lines.append(f"Override Reason: {override_reason}")

    lines.append(f"Disclaimer: {DISCLAIMER}")
    return "\n".join(lines).encode()
