from core.checklist import build_document_checklist
from export.pdf_export import build_prequal_pdf


def test_build_document_checklist():
    income_cards = [
        {"type": "w2", "payload": {}},
        {"type": "schc", "payload": {}},
        {"type": "other", "payload": {"Type": "Child Support"}},
    ]
    docs = build_document_checklist(income_cards)
    assert "Last two pay stubs" in docs
    assert "W-2s" in docs
    assert "1040s" in docs
    assert "Business bank statements" in docs
    assert "Child support court orders" in docs
    assert len(docs) == len(set(docs))


def test_pdf_export_includes_checklist():
    data = {
        "checklist": [
            {"label": "Last two pay stubs", "checked": True},
            {"label": "W-2s", "checked": False},
        ]
    }
    output = build_prequal_pdf(data)
    assert b"[x] Last two pay stubs" in output
    assert b"[ ] W-2s" in output
