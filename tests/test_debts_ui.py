from streamlit.testing.v1 import AppTest


def debts_app():
    import streamlit as st
    from ui.cards_debts import render_debt_cards

    render_debt_cards()


def test_payoff_flag_excludes_from_total():
    at = AppTest.from_function(debts_app)
    at.session_state["debt_cards"] = [
        {
            "type": "installment",
            "payload": {
                "name": "A",
                "monthly_payment": 100.0,
                "remaining_payments": 0,
                "payoff_at_close": True,
            },
        },
        {
            "type": "installment",
            "payload": {
                "name": "B",
                "monthly_payment": 200.0,
                "remaining_payments": 0,
                "payoff_at_close": False,
            },
        },
    ]
    at.run()
    md = next(m.value for m in at.markdown if "Total Monthly Debts" in m.value)
    assert "$200.00" in md
