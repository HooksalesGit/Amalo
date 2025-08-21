"""Placeholders for future external service integrations."""

from __future__ import annotations


def fetch_credit_report(ssn: str) -> dict:
    """Stub for credit report API integration."""
    raise NotImplementedError("Credit report integration not implemented")


def get_property_valuation(address: str) -> float:
    """Stub for property valuation API integration."""
    raise NotImplementedError("Property valuation integration not implemented")


def analyze_bank_statements(data: bytes) -> dict:
    """Stub for bank statement analysis integration."""
    raise NotImplementedError("Bank statement analysis not implemented")
