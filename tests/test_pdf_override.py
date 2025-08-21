import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from export.pdf_export import build_prequal_pdf


def test_requires_override_with_critical():
    data = {
        "warnings": [{"severity": "critical", "message": "K-1 used but distributions not verified."}],
        "checklist": [],
    }
    with pytest.raises(ValueError):
        build_prequal_pdf(data)


def test_override_included():
    data = {
        "warnings": [{"severity": "critical", "message": "K-1 used but distributions not verified."}],
        "override_reason": "Borrower provided liquidity statement",
        "checklist": [],
    }
    output = build_prequal_pdf(data)
    assert b"Override Reason: Borrower provided liquidity statement" in output
