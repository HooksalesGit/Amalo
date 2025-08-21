"""Placeholders for future external service integrations."""


def fetch_credit_report(borrower_id: int) -> dict:
    """Stub for credit report integration."""
    raise NotImplementedError("Credit report API integration not implemented")


def fetch_property_valuation(address: str) -> float:
    """Stub for property valuation services."""
    raise NotImplementedError("Property valuation API integration not implemented")


def analyze_bank_statements(statements: list) -> dict:
    """Stub for bank statement analysis."""
    raise NotImplementedError("Bank statement analysis not implemented")
