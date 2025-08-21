from core.rules import evaluate_rules


def _codes(state):
    return {r.code for r in evaluate_rules(state)}


def test_missing_variable_months():
    codes = _codes({"total_income": 1000, "w2_meta": {"var_missing_months": 2}})
    assert "W2_VAR_MISSING_MONTHS" in codes


def test_total_income_decline():
    state = {"total_income": 1000, "total_income_history": {2023: 100000, 2024: 75000}}
    codes = _codes(state)
    assert "TOTAL_INCOME_DECLINE" in codes


def test_negative_rental_income():
    codes = _codes({"total_income": 1000, "rental_income": -50})
    assert "RENTAL_INCOME_NEGATIVE" in codes


def test_ratio_and_dti_limits():
    state = {"total_income": 1000, "FE": 0.35, "BE": 0.5, "target_FE": 31, "target_BE": 45}
    codes = _codes(state)
    assert "HOUSING_RATIO_OVER_LIMIT" in codes
    assert "TOTAL_DTI_OVER_LIMIT" in codes


def test_reserves_prompt():
    state_high_dti = {"total_income": 1000, "BE": 0.5}
    state_invest = {"total_income": 1000, "is_investment_property": True}
    assert "CONSIDER_RESERVES" in _codes(state_high_dti)
    assert "CONSIDER_RESERVES" in _codes(state_invest)
