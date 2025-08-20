import pandas as pd
from core.calculators import monthly_payment, principal_from_payment, max_affordable_pi, rentals_policy, apply_program_fees
from core.presets import CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE

def test_amortization_inverse_roundtrip():
    principal=400000; rate=6.5; term=30
    pmt = monthly_payment(principal, rate, term)
    back = principal_from_payment(pmt, rate, term)
    assert abs(back - principal) < 1.5

def test_max_affordable_pi():
    fe, be, cons = max_affordable_pi(12000, 500, 800, 31, 45)
    assert cons <= fe and cons <= be
    assert cons >= 0

def test_rentals_policy_schedule_e():
    df = pd.DataFrame([{"BorrowerID":1,"Property":"A","Year":2024,"Rents":24000,"Expenses":12000,"Depreciation":3000}])
    agg = rentals_policy(df, method="ScheduleE")
    assert round(float(agg.loc[0,"Rental_Monthly"]),2) == round((24000-12000+3000)/12,2)

def test_program_fees_va_financed():
    res = apply_program_fees("VA", 500000, 450000, 50000, 6.5, 30, CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE, True, True, ">=740")
    assert res["adjusted_loan"] > 450000
