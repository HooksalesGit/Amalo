import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.calculators import (
    monthly_payment,
    principal_from_payment,
    max_affordable_pi,
    max_qualifying_loan,
    rentals_policy,
    default_gross_up_pct,
    filter_support_income,
    apply_program_fees,
    sch_c_totals,
    w2_totals,
    k1_totals,
)
from core.presets import CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE


def test_amortization_inverse_roundtrip():
    principal = 400000
    rate = 6.5
    term = 30
    pmt = monthly_payment(principal, rate, term)
    back = principal_from_payment(pmt, rate, term)
    assert abs(back - principal) < 1.5


def test_max_affordable_pi():
    fe, be, cons = max_affordable_pi(12000, 500, 800, 31, 45)
    assert cons <= fe and cons <= be
    assert cons >= 0


def test_max_qualifying_loan_fha_financed():
    res = max_qualifying_loan(
        10000,
        500,
        300,
        31,
        45,
        6.5,
        30,
        20000,
        "FHA",
        CONV_MI_BANDS,
        FHA_TABLES,
        VA_TABLE,
        USDA_TABLE,
        True,
        True,
        ">=740",
    )
    assert res["adjusted_loan"] >= res["base_loan"]
    assert abs(res["purchase_price"] - (res["base_loan"] + 20000)) < 1e-6


def test_apply_program_fees_financed_ltv():
    res = apply_program_fees(
        "FHA",
        300000,
        285000,
        15000,
        6.5,
        30,
        CONV_MI_BANDS,
        FHA_TABLES,
        VA_TABLE,
        USDA_TABLE,
        True,
        True,
        ">=740",
    )
    assert abs(res["ltv"] - (res["adjusted_loan"] / 300000 * 100)) < 1e-6


def test_rentals_policy_schedule_e():
    df = pd.DataFrame(
        [{"BorrowerID": 1, "Property": "A", "Year": 2024, "Rents": 24000, "Expenses": 12000, "Depreciation": 3000}]
    )
    agg = rentals_policy(df, method="ScheduleE")
    expected = (24000 - 12000 + 3000) / 12
    assert round(float(agg.loc[0, "Rental_Monthly"]), 2) == round(expected, 2)


def test_program_fees_va_financed():
    res = apply_program_fees(
        "VA",
        500000,
        450000,
        50000,
        6.5,
        30,
        CONV_MI_BANDS,
        FHA_TABLES,
        VA_TABLE,
        USDA_TABLE,
        True,
        True,
        ">=740",
    )
    assert res["adjusted_loan"] > 450000


def test_sch_c_totals_declining_flag():
    df = pd.DataFrame(
        [
            {"BorrowerID": 1, "Year": 2023, "NetProfit": 100000},
            {"BorrowerID": 1, "Year": 2024, "NetProfit": 70000},
            {"BorrowerID": 2, "Year": 2023, "NetProfit": 50000},
            {"BorrowerID": 2, "Year": 2024, "NetProfit": 60000},
        ]
    )
    res = sch_c_totals(df)
    b1 = bool(res.loc[res["BorrowerID"] == 1, "SchC_DecliningFlag"].iloc[0])
    b2 = bool(res.loc[res["BorrowerID"] == 2, "SchC_DecliningFlag"].iloc[0])
    assert b1 and not b2


def test_w2_totals_avg_and_flags():
    df = pd.DataFrame(
        [
            {
                "BorrowerID": 1,
                "PayType": "Hourly",
                "HourlyRate": 20,
                "HoursPerWeek": 40,
                "OT_YTD": 1200,
                "Bonus_YTD": 0,
                "Comm_YTD": 0,
                "Months_YTD": 6,
                "OT_LY": 2400,
                "Bonus_LY": 0,
                "Comm_LY": 0,
                "Months_LY": 12,
                "VarAvgMonths": 24,
                "IncludeVariable": 1,
            }
        ]
    )
    res = w2_totals(df)
    bm = float(res.loc[0, "BaseMonthly"])
    vm = float(res.loc[0, "VariableMonthly"])
    assert round(bm, 2) == round(20 * 40 * 52 / 12, 2)
    assert round(vm, 2) == round((1200 + 2400) / 24, 2)
    assert not bool(res.loc[0, "W2_InsufficientVarFlag"])


def test_w2_totals_clips_negatives_and_warns():
    df = pd.DataFrame(
        [
            {
                "BorrowerID": 1,
                "PayType": "Salary",
                "AnnualSalary": 60000,
                "OT_YTD": -500,
                "Bonus_YTD": 0,
                "Comm_YTD": 0,
                "Months_YTD": 2,
                "OT_LY": 0,
                "Bonus_LY": 0,
                "Comm_LY": 0,
                "Months_LY": 0,
                "IncludeVariable": 1,
            }
        ]
    )
    res = w2_totals(df)
    assert float(res.loc[0, "VariableMonthly"]) == 0.0
    assert bool(res.loc[0, "W2_InsufficientVarFlag"])


def test_w2_base_decline_flag():
    df = pd.DataFrame(
        [
            {"BorrowerID": 1, "PayType": "Salary", "AnnualSalary": 40000, "Base_LY": 60000, "IncludeVariable": 0},
            {"BorrowerID": 2, "PayType": "Salary", "AnnualSalary": 50000, "Base_LY": 50000, "IncludeVariable": 0},
        ]
    )
    res = w2_totals(df)
    b1 = bool(res.loc[res["BorrowerID"] == 1, "W2_DecliningBaseFlag"].iloc[0])
    b2 = bool(res.loc[res["BorrowerID"] == 2, "W2_DecliningBaseFlag"].iloc[0])
    assert b1 and not b2


def test_sch_c_recent_only_toggle():
    df = pd.DataFrame(
        [
            {"BorrowerID": 1, "Year": 2023, "NetProfit": 100000},
            {"BorrowerID": 1, "Year": 2024, "NetProfit": 50000},
        ]
    )
    avg = sch_c_totals(df)
    recent = sch_c_totals(df, recent_only=True)
    assert round(float(avg.loc[0, "SchC_Monthly"]), 2) == round((100000 + 50000) / 2 / 12, 2)
    assert round(float(recent.loc[0, "SchC_Monthly"]), 2) == round(50000 / 12, 2)


def test_k1_declining_flag():
    df = pd.DataFrame(
        [
            {"BorrowerID": 1, "Year": 2023, "OwnershipPct": 50, "Ordinary": 80000},
            {"BorrowerID": 1, "Year": 2024, "OwnershipPct": 50, "Ordinary": 40000},
        ]
    )
    res = k1_totals(df)
    assert bool(res.loc[0, "K1_DecliningFlag"])


def test_rental_declining_flag():
    df = pd.DataFrame(
        [
            {"BorrowerID": 1, "Property": "A", "Year": 2023, "Rents": 24000, "Expenses": 12000, "Depreciation": 3000},
            {"BorrowerID": 1, "Property": "A", "Year": 2024, "Rents": 18000, "Expenses": 12000, "Depreciation": 3000},
        ]
    )
    res = rentals_policy(df, method="ScheduleE")
    assert bool(res.loc[0, "Rental_DecliningFlag"])


def test_rentals_policy_75pct_subject_pitia():
    df = pd.DataFrame(
        [{"BorrowerID": 1, "Property": "A", "Year": 2024, "Rents": 12000, "Expenses": 0, "Depreciation": 0}]
    )
    agg = rentals_policy(
        df,
        method="SeventyFivePctGross",
        subject_pitia=1000,
        subject_market_rent=2000,
    )
    expected = 0.75 * (12000 / 12) + 0.75 * 2000 - 1000
    assert round(float(agg.loc[0, "Rental_Monthly"]), 2) == round(expected, 2)


def test_default_gross_up_pct():
    assert default_gross_up_pct("Social Security", "FHA") == 25.0
    assert default_gross_up_pct("Disability", "Conventional") == 15.0
    assert default_gross_up_pct("Unknown", "VA") == 0.0


def test_filter_support_income():
    df = pd.DataFrame(
        [
            {"BorrowerID": 1, "Type": "Alimony", "GrossMonthly": 1000, "GrossUpPct": 0},
            {"BorrowerID": 1, "Type": "Housing Allowance", "GrossMonthly": 500, "GrossUpPct": 0},
            {"BorrowerID": 1, "Type": "Bonus", "GrossMonthly": 300, "GrossUpPct": 0},
        ]
    )
    flt = filter_support_income(df, False)
    assert all(~flt["Type"].str.lower().str.contains("alimony|housing"))
    assert len(flt) == 1

