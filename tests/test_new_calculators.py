from core.calculators import (
    compare_scenarios,
    dscr,
    reserve_requirement,
    what_if_max_qualifying,
)
from core.presets import CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE


def test_reserve_requirement_primary_investment():
    assert reserve_requirement(2000, "primary", "Conventional") == 4000
    assert reserve_requirement(2000, "investment", "Conventional") == 12000


def test_dscr_flagging():
    low = dscr(1800, 2000, "Conventional")
    high = dscr(2200, 2000, "Conventional")
    assert low["below_minimum"] is True
    assert high["below_minimum"] is False


def test_what_if_max_qualifying_changes():
    res = what_if_max_qualifying(
        10000,
        500,
        300,
        31,
        45,
        6.5,
        30,
        20000,
        "Conventional",
        CONV_MI_BANDS,
        FHA_TABLES,
        VA_TABLE,
        USDA_TABLE,
        True,
        True,
        ">=740",
    )
    base = res["base"]
    dp = res["down_payment_plus_10k"]
    rate = res["rate_plus_0.25"]
    debt = res["debt_plus_300"]
    assert dp["max_loan"] >= base["max_loan"]
    assert rate["max_loan"] < base["max_loan"]
    assert debt["be_dti"] > base["be_dti"]


def test_compare_scenarios_rate_and_down_payment():
    res = compare_scenarios(
        10000,
        500,
        300,
        31,
        45,
        6.5,
        30,
        20000,
        "Conventional",
        CONV_MI_BANDS,
        FHA_TABLES,
        VA_TABLE,
        USDA_TABLE,
        True,
        True,
        ">=740",
        alt_rate_pct=6.0,
        alt_down_payment_amt=30000,
    )
    assert res["alt"]["max_purchase"] > res["base"]["max_purchase"]
