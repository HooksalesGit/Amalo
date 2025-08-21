from streamlit.testing.v1 import AppTest
from core.calculators import monthly_payment


def housing_app():
    import app

    app.render_property_column()


def test_pi_calculator_updates():
    at = AppTest.from_function(housing_app)
    at.session_state["housing"] = {
        "purchase_price": 100000.0,
        "down_payment_amt": 20000.0,
        "rate_pct": 5.0,
        "term_years": 30,
        "tax_rate_pct": 0.0,
        "hoi_annual": 0.0,
        "hoa_monthly": 0.0,
        "finance_upfront": True,
    }
    at.run()
    base_loan = 80000.0
    expected = monthly_payment(base_loan, 5.0, 30)
    pi_caption = next(c.value for c in at.caption if c.value.startswith("Monthly P&I"))
    assert pi_caption == f"Monthly P&I: ${expected:,.2f}"

    rate_widget = next(w for w in at.number_input if w.label == "Rate %")
    term_widget = next(w for w in at.number_input if w.label == "Term (years)")
    rate_widget.set_value(7.0)
    term_widget.set_value(15)
    at.run()
    expected2 = monthly_payment(base_loan, 7.0, 15)
    pi_caption2 = next(c.value for c in at.caption if c.value.startswith("Monthly P&I"))
    assert pi_caption2 == f"Monthly P&I: ${expected2:,.2f}"


def test_hoi_rate_pct_used_for_annual():
    at = AppTest.from_function(housing_app)
    at.session_state["housing"] = {
        "purchase_price": 200000.0,
        "down_payment_amt": 0.0,
        "rate_pct": 5.0,
        "term_years": 30,
        "tax_rate_pct": 0.0,
        "hoi_annual": 0.0,
        "hoi_rate_pct": 1.0,
        "hoa_monthly": 0.0,
        "finance_upfront": True,
    }
    at.run()
    expected_hoi = 200000.0 * 1.0 / 100 / 12
    assert abs(at.session_state["housing_calc"]["hoi"] - expected_hoi) < 1e-6


def test_financed_fee_displays_adjusted_loan():
    at = AppTest.from_function(housing_app)
    at.session_state["program_name"] = "FHA"
    at.session_state["housing"] = {
        "purchase_price": 200000.0,
        "down_payment_amt": 10000.0,
        "rate_pct": 5.0,
        "term_years": 30,
        "tax_rate_pct": 0.0,
        "hoi_annual": 0.0,
        "hoa_monthly": 0.0,
        "finance_upfront": True,
        "first_use_va": True,
    }
    at.run()
    caption = next(c.value for c in at.caption if "Base Loan" in c.value)
    assert "Adjusted Loan" in caption
