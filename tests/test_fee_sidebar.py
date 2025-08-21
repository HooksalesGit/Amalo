import json
from streamlit.testing.v1 import AppTest


def sidebar_app():
    import app
    app.render_fee_sidebar()
    app.render_property_column()


def test_conventional_mi_table_editable():
    at = AppTest.from_function(sidebar_app)
    at.session_state["program_name"] = "Conventional"
    at.session_state["housing"] = {
        "purchase_price": 200000.0,
        "down_payment_amt": 20000.0,
        "rate_pct": 5.0,
        "term_years": 30,
        "tax_rate_pct": 0.0,
        "hoi_annual": 0.0,
        "hoa_monthly": 0.0,
        "finance_upfront": True,
        "credit_score": 700,
    }
    at.run()
    base_loan = 180000.0
    default_mi = at.session_state["housing_calc"]["mi"]
    assert abs(default_mi - base_loan * (0.40 / 100) / 12) < 1e-6

    # modify the sidebar table for the <720 fico bucket and rerun
    ta = next(w for w in at.sidebar.text_area if w.label == "Conventional MI Table")
    tbl = at.session_state["conv_mi_table"]
    tbl["<720"]["90-95"] = 1.00
    ta.set_value(json.dumps(tbl, indent=2))
    at.run()
    updated_mi = at.session_state["housing_calc"]["mi"]
    assert abs(updated_mi - base_loan * (1.00 / 100) / 12) < 1e-6
    assert updated_mi != default_mi
