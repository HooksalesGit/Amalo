
from __future__ import annotations
import math
import pandas as pd


def nz(x, default=0.0):
    """Return a float for ``x`` or a fallback value.

    Many calculations pull values from uploaded spreadsheets where empty cells
    appear as ``None`` or ``NaN``.  This helper mirrors the spreadsheet
    ``NZ()`` function and keeps later math from breaking when a value is
    missing.
    """

    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return default
        return float(x)
    except Exception:
        return default


def nz_series(s):
    """Coerce a sequence/Series to numeric with missing values as ``0``.

    Mortgage income worksheets often have blank cells.  Converting them to
    numeric zeros simplifies downstream aggregation logic.
    """

    if s is None:
        return 0.0
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def monthly_payment(principal, annual_rate_pct, term_years):
    """Calculate the fully amortizing monthly payment for a loan.

    ``principal`` is the starting loan amount, ``annual_rate_pct`` is the
    nominal yearly interest rate (e.g. ``6.5`` for 6.5%), and ``term_years`` is
    the amortization period in years.
    """

    L = nz(principal)
    r = nz(annual_rate_pct) / 100 / 12
    n = int(nz(term_years) * 12)
    if n <= 0:
        return 0.0
    if abs(r) < 1e-9:
        return L / n
    return (r * L) / (1 - (1 + r) ** (-n))


def principal_from_payment(payment, annual_rate_pct, term_years):
    """Reverse amortization to find the loan amount for a given payment.

    This is useful when qualifying a borrower: given a payment target, rate and
    term, determine the maximum principal that fits the scenario.
    """

    P = nz(payment)
    r = nz(annual_rate_pct) / 100 / 12
    n = int(nz(term_years) * 12)
    if n <= 0:
        return 0.0
    if abs(r) < 1e-9:
        return P * n
    return P * (1 - (1 + r) ** (-n)) / r


def w2_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize W‑2 income to monthly amounts for each borrower.

    The function separates stable base pay from variable earnings such as
    overtime, bonus and commission.  It also flags when current year variable
    income is trending down more than 20% versus the prior year—a common
    underwriting concern.
    """

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "BorrowerID",
                "BaseMonthly",
                "VariableMonthly",
                "QualMonthly",
                "W2_DecliningVarFlag",
            ]
        )
    out = df.copy()

    num_cols = [
        "AnnualSalary",
        "HourlyRate",
        "HoursPerWeek",
        "OT_YTD",
        "Bonus_YTD",
        "Comm_YTD",
        "Months_YTD",
        "OT_LY",
        "Bonus_LY",
        "Comm_LY",
        "Months_LY",
        "Base_LY",
    ]
    for c in num_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0).clip(lower=0)
        else:
            out[c] = 0.0
    if "VarAvgMonths" in out.columns:
        out["VarAvgMonths"] = pd.to_numeric(out["VarAvgMonths"], errors="coerce").fillna(12)
    else:
        out["VarAvgMonths"] = 12

    def base_monthly(r):
        t = str(r.get("PayType", "")).lower()
        if t == "salary":
            return nz(r.get("AnnualSalary")) / 12
        if t == "hourly":
            return nz(r.get("HourlyRate")) * nz(r.get("HoursPerWeek")) * 52 / 12
        return 0.0

    out["BaseMonthly"] = out.apply(base_monthly, axis=1)
    out["VarTotal"] = (
        out[["OT_YTD", "Bonus_YTD", "Comm_YTD"]].sum(axis=1)
        + out[["OT_LY", "Bonus_LY", "Comm_LY"]].sum(axis=1)
    )
    hist_months = out["Months_YTD"] + out["Months_LY"]
    out["InsufficientHistory"] = hist_months < 12
    out["VarMonths"] = hist_months
    out.loc[out["VarAvgMonths"] == 24, "VarMonths"] = 24
    out.loc[out["VarAvgMonths"] != 24, "VarMonths"] = out.loc[
        out["VarAvgMonths"] != 24, "VarMonths"
    ].replace(0, pd.NA)
    out["VariableMonthly"] = (out["VarTotal"] / out["VarMonths"]).fillna(0)
    out["YOY_Var_Annualized"] = (
        (
            out[["OT_YTD", "Bonus_YTD", "Comm_YTD"]].fillna(0).sum(axis=1)
        )
        / (out["Months_YTD"].replace(0, pd.NA))
        * 12
    ).fillna(0)
    out["DecliningVarFlag"] = (
        out["OT_LY"].fillna(0)
        + out["Bonus_LY"].fillna(0)
        + out["Comm_LY"].fillna(0)
    ) > (1.2 * out["YOY_Var_Annualized"])
    out["BaseAnnual"] = out["BaseMonthly"] * 12
    out["DecliningBaseFlag"] = out["Base_LY"].fillna(0) > (1.2 * out["BaseAnnual"])
    out["IncludeVariable"] = out["IncludeVariable"].fillna(0).astype(float)
    out["QualMonthly_row"] = out["BaseMonthly"] + out["IncludeVariable"] * out["VariableMonthly"]
    agg = (
        out.groupby("BorrowerID", dropna=False)
        .agg(
            BaseMonthly=("BaseMonthly", "sum"),
            VariableMonthly=("VariableMonthly", "sum"),
            QualMonthly=("QualMonthly_row", "sum"),
            W2_DecliningVarFlag=("DecliningVarFlag", "any"),
            W2_DecliningBaseFlag=("DecliningBaseFlag", "any"),
            W2_InsufficientVarFlag=("InsufficientHistory", "any"),
        )
        .reset_index()
    )
    return agg

def sch_c_totals(df: pd.DataFrame, recent_only: bool = False) -> pd.DataFrame:
    """Calculate Schedule C business income averaged to monthly amounts.

    Net profit from sole proprietorships is adjusted with common add‑backs such
    as depreciation and depletion.  The function also flags when income is
    declining year‑over‑year by more than 20%.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=["BorrowerID", "SchC_Monthly", "SchC_DecliningFlag"])
    out = df.copy()
    out["MileageDep"] = out.apply(lambda r: nz(r.get("BusinessMiles")) * nz(r.get("MileDepRate")), axis=1)
    out["AdjustedAnnual"] = (
        nz_series(out.get("NetProfit"))
        + nz_series(out.get("Nonrecurring"))
        + nz_series(out.get("Depletion"))
        + nz_series(out.get("Depreciation"))
        - nz_series(out.get("NonDedMeals"))
        + nz_series(out.get("UseOfHome"))
        + nz_series(out.get("AmortCasualty"))
        + nz_series(out.get("MileageDep"))
    )
    by_year = out.groupby(["BorrowerID", "Year"], dropna=False)["AdjustedAnnual"].sum().reset_index()
    by_year["AdjustedAnnual"] = pd.to_numeric(by_year["AdjustedAnnual"], errors="coerce").fillna(0.0)
    by_year = by_year.sort_values(["BorrowerID", "Year"])

    def decline_flag(s: pd.Series) -> bool:
        if len(s) < 2:
            return False
        return bool(s.iloc[-1] < 0.8 * s.iloc[-2])

    flags = by_year.groupby("BorrowerID")["AdjustedAnnual"].apply(decline_flag).reset_index()
    flags.rename(columns={"AdjustedAnnual": "SchC_DecliningFlag"}, inplace=True)
    if recent_only:
        latest = by_year.groupby("BorrowerID", dropna=False).last().reset_index()
        latest["SchC_Monthly"] = latest["AdjustedAnnual"] / 12
        res = latest[["BorrowerID", "SchC_Monthly"]]
    else:
        avg = by_year.groupby("BorrowerID", dropna=False)["AdjustedAnnual"].mean().reset_index()
        avg["SchC_Monthly"] = avg["AdjustedAnnual"] / 12
        res = avg[["BorrowerID", "SchC_Monthly"]]
    return res.merge(flags, on="BorrowerID", how="left")[
        ["BorrowerID", "SchC_Monthly", "SchC_DecliningFlag"]
    ]

def k1_totals(df: pd.DataFrame, recent_only: bool = False) -> pd.DataFrame:
    """Average partnership or S‑corp income from K‑1 statements."""

    if df is None or df.empty:
        return pd.DataFrame(columns=["BorrowerID", "K1_Monthly", "K1_DecliningFlag"])
    out = df.copy()
    out["AdjustedAnnual"] = (
        nz_series(out.get("Ordinary"))
        + nz_series(out.get("NetRentalOther"))
        + nz_series(out.get("GuaranteedPmt"))
        + nz_series(out.get("Nonrecurring"))
        + nz_series(out.get("Depreciation"))
        + nz_series(out.get("Depletion"))
        + nz_series(out.get("AmortCasualty"))
        - nz_series(out.get("NotesLT1yr"))
        - nz_series(out.get("NonDed_TandE"))
    )
    out["AfterOwnership"] = nz_series(out.get("OwnershipPct")) / 100 * out["AdjustedAnnual"]
    by_year = out.groupby(["BorrowerID", "Year"], dropna=False)["AfterOwnership"].sum().reset_index()
    by_year = by_year.sort_values(["BorrowerID", "Year"])

    def decline_flag(s: pd.Series) -> bool:
        if len(s) < 2:
            return False
        return bool(s.iloc[-1] < 0.8 * s.iloc[-2])

    flags = by_year.groupby("BorrowerID")["AfterOwnership"].apply(decline_flag).reset_index()
    flags.rename(columns={"AfterOwnership": "K1_DecliningFlag"}, inplace=True)
    if recent_only:
        latest = by_year.groupby("BorrowerID", dropna=False).last().reset_index()
        latest["K1_Monthly"] = latest["AfterOwnership"] / 12
        res = latest[["BorrowerID", "K1_Monthly"]]
    else:
        avg = by_year.groupby("BorrowerID", dropna=False)["AfterOwnership"].mean().reset_index()
        avg["K1_Monthly"] = avg["AfterOwnership"] / 12
        res = avg[["BorrowerID", "K1_Monthly"]]
    return res.merge(flags, on="BorrowerID", how="left")[
        ["BorrowerID", "K1_Monthly", "K1_DecliningFlag"]
    ]

def ccorp_totals(df: pd.DataFrame, recent_only: bool = False) -> pd.DataFrame:
    """Determine income from a wholly owned C‑Corporation (Form 1120)."""

    if df is None or df.empty:
        return pd.DataFrame(columns=["BorrowerID","C1120_Monthly", "C1120_DecliningFlag"])
    out = df.copy()
    out = out[nz_series(out.get("OwnershipPct")) >= 100].copy()
    out["AdjustedAnnual"] = (
        nz_series(out.get("TaxableIncome")) - nz_series(out.get("TotalTax")) + nz_series(out.get("Nonrecurring")) +
        nz_series(out.get("OtherIncLoss")) + nz_series(out.get("Depreciation")) + nz_series(out.get("Depletion")) +
        nz_series(out.get("AmortCasualty")) - nz_series(out.get("NotesLT1yr")) - nz_series(out.get("NonDed_TandE")) - nz_series(out.get("DividendsPaid"))
    )
    by_year = out.groupby(["BorrowerID","Year"], dropna=False)["AdjustedAnnual"].sum().reset_index()
    by_year = by_year.sort_values(["BorrowerID", "Year"])

    def decline_flag(s: pd.Series) -> bool:
        if len(s) < 2:
            return False
        return bool(s.iloc[-1] < 0.8 * s.iloc[-2])

    flags = by_year.groupby("BorrowerID")["AdjustedAnnual"].apply(decline_flag).reset_index()
    flags.rename(columns={"AdjustedAnnual": "C1120_DecliningFlag"}, inplace=True)
    if recent_only:
        latest = by_year.groupby("BorrowerID", dropna=False).last().reset_index()
        latest["C1120_Monthly"] = latest["AdjustedAnnual"] / 12
        res = latest[["BorrowerID","C1120_Monthly"]]
    else:
        avg = by_year.groupby("BorrowerID", dropna=False)["AdjustedAnnual"].mean().reset_index()
        avg["C1120_Monthly"] = avg["AdjustedAnnual"] / 12
        res = avg[["BorrowerID","C1120_Monthly"]]
    return res.merge(flags, on="BorrowerID", how="left")[
        ["BorrowerID","C1120_Monthly", "C1120_DecliningFlag"]
    ]

def rentals_policy(
    df: pd.DataFrame, method="ScheduleE", subject_pitia=0.0, subject_market_rent=0.0
):
    """Qualify rental income using tax returns or market rent.

    ``method`` controls the approach:

    * ``"ScheduleE"`` – uses Schedule E net income with depreciation add-back.
    * otherwise – uses 75% of gross rent and optionally credits subject property
      market rent minus PITI.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=["BorrowerID", "Rental_Monthly"])
    out = df.copy()
    if method == "ScheduleE":
        out["NetAnnual"] = (
            nz_series(out.get("Rents"))
            - nz_series(out.get("Expenses"))
            + nz_series(out.get("Depreciation"))
        )
        by_year = out.groupby(["BorrowerID", "Year"], dropna=False)["NetAnnual"].sum().reset_index()
        by_year = by_year.sort_values(["BorrowerID", "Year"])

        def decline_flag(s: pd.Series) -> bool:
            if len(s) < 2:
                return False
            return bool(s.iloc[-1] < 0.8 * s.iloc[-2])

        flags = by_year.groupby("BorrowerID")["NetAnnual"].apply(decline_flag).reset_index()
        flags.rename(columns={"NetAnnual": "Rental_DecliningFlag"}, inplace=True)
        avg = by_year.groupby("BorrowerID", dropna=False)["NetAnnual"].mean().reset_index()
        avg["Rental_Monthly"] = avg["NetAnnual"] / 12
        return avg.merge(flags, on="BorrowerID", how="left")[
            ["BorrowerID", "Rental_Monthly", "Rental_DecliningFlag"]
        ]
    else:
        out["GrossMonthly"] = nz_series(out.get("Rents")) / 12
        agg = out.groupby("BorrowerID", dropna=False)["GrossMonthly"].sum().reset_index()
        agg["Rental_Monthly"] = 0.75 * agg["GrossMonthly"]
        if nz(subject_market_rent) > 0:
            mask = agg["BorrowerID"] == 1
            if any(mask):
                agg.loc[mask, "Rental_Monthly"] += 0.75 * nz(subject_market_rent) - nz(subject_pitia)
        agg["Rental_DecliningFlag"] = False
        return agg[["BorrowerID", "Rental_Monthly", "Rental_DecliningFlag"]]

def other_income_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate miscellaneous income sources such as alimony or SSA.

    Non‑taxable income can be grossed up by the ``GrossUpPct`` column to reflect
    qualifying income for mortgage purposes.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=["BorrowerID", "Other_Monthly"])
    out = df.copy()
    out["QualMonthly"] = nz_series(out.get("GrossMonthly")) * (
        1.0 + nz_series(out.get("GrossUpPct")) / 100
    )
    agg = out.groupby("BorrowerID", dropna=False)["QualMonthly"].sum().reset_index()
    agg.rename(columns={"QualMonthly": "Other_Monthly"}, inplace=True)
    return agg

def combine_income(
    num_borrowers: int,
    w2=None,
    schc=None,
    k1=None,
    c1120=None,
    rentals=None,
    other=None,
    recent_selfemp: bool = False,
) -> pd.DataFrame:
    """Merge all income sources into a single table per borrower."""

    base = pd.DataFrame({"BorrowerID": list(range(1, num_borrowers + 1))})

    def mergecol(L, R, col):
        if R is None or R.empty:
            R = pd.DataFrame(columns=["BorrowerID", col])
        return L.merge(R[["BorrowerID", col]], on="BorrowerID", how="left")

    w2a = w2_totals(w2) if w2 is not None else pd.DataFrame(columns=["BorrowerID", "QualMonthly", "W2_DecliningVarFlag", "W2_DecliningBaseFlag"])
    w2a = w2a.rename(columns={"QualMonthly": "W2_Monthly"})
    sca = sch_c_totals(schc, recent_only=recent_selfemp) if schc is not None else pd.DataFrame(columns=["BorrowerID", "SchC_Monthly", "SchC_DecliningFlag"])
    k1a = k1_totals(k1, recent_only=recent_selfemp) if k1 is not None else pd.DataFrame(columns=["BorrowerID", "K1_Monthly", "K1_DecliningFlag"])
    c1a = ccorp_totals(c1120, recent_only=recent_selfemp) if c1120 is not None else pd.DataFrame(columns=["BorrowerID", "C1120_Monthly", "C1120_DecliningFlag"])
    ra = rentals if rentals is not None else pd.DataFrame(columns=["BorrowerID", "Rental_Monthly", "Rental_DecliningFlag"])
    oa = other_income_totals(other) if other is not None else pd.DataFrame(columns=["BorrowerID", "Other_Monthly"])

    out = base.copy()
    out = mergecol(out, w2a, "W2_Monthly")
    if "W2_DecliningVarFlag" in w2a.columns:
        out = out.merge(w2a[["BorrowerID", "W2_DecliningVarFlag"]], on="BorrowerID", how="left")
    if "W2_DecliningBaseFlag" in w2a.columns:
        out = out.merge(w2a[["BorrowerID", "W2_DecliningBaseFlag"]], on="BorrowerID", how="left")
    if "W2_InsufficientVarFlag" in w2a.columns:
        out = out.merge(w2a[["BorrowerID", "W2_InsufficientVarFlag"]], on="BorrowerID", how="left")
    out = mergecol(out, sca, "SchC_Monthly")
    if "SchC_DecliningFlag" in sca.columns:
        out = out.merge(sca[["BorrowerID", "SchC_DecliningFlag"]], on="BorrowerID", how="left")
    out = mergecol(out, k1a, "K1_Monthly")
    if "K1_DecliningFlag" in k1a.columns:
        out = out.merge(k1a[["BorrowerID", "K1_DecliningFlag"]], on="BorrowerID", how="left")
    out = mergecol(out, c1a, "C1120_Monthly")
    if "C1120_DecliningFlag" in c1a.columns:
        out = out.merge(c1a[["BorrowerID", "C1120_DecliningFlag"]], on="BorrowerID", how="left")
    out = mergecol(out, ra, "Rental_Monthly")
    if "Rental_DecliningFlag" in ra.columns:
        out = out.merge(ra[["BorrowerID", "Rental_DecliningFlag"]], on="BorrowerID", how="left")
    out = mergecol(out, oa, "Other_Monthly")
    for c in [
        "W2_Monthly",
        "SchC_Monthly",
        "K1_Monthly",
        "C1120_Monthly",
        "Rental_Monthly",
        "Other_Monthly",
    ]:
        out[c] = out[c].fillna(0.0)
    out["TotalMonthlyIncome"] = out[
        [
            "W2_Monthly",
            "SchC_Monthly",
            "K1_Monthly",
            "C1120_Monthly",
            "Rental_Monthly",
            "Other_Monthly",
        ]
    ].sum(axis=1)
    out["AnyDecliningFlag"] = out[
        [
            "W2_DecliningVarFlag",
            "W2_DecliningBaseFlag",
            "SchC_DecliningFlag",
            "K1_DecliningFlag",
            "C1120_DecliningFlag",
            "Rental_DecliningFlag",
        ]
    ].fillna(False).any(axis=1)
    return out

def compute_ltv(purchase_price, base_loan):
    """Compute loan‑to‑value percentage."""

    if nz(purchase_price) == 0:
        return 0.0
    return 100.0 * nz(base_loan) / nz(purchase_price)


def conventional_mi_factor(ltv, fico_bucket, mi_table):
    """Look up private MI factor based on LTV and credit score bucket."""

    if ltv >= 97:
        return mi_table.get(">=97", 0.90)
    if 95 <= ltv < 97:
        return mi_table.get("95-97", 0.62)
    if 90 <= ltv < 95:
        return mi_table.get("90-95", 0.40)
    if 85 <= ltv < 90:
        return mi_table.get("85-90", 0.25)
    return mi_table.get("<85", 0.0)


def fha_mip_factor(ltv, term_years, table):
    """Retrieve FHA annual MIP factor from lookup table."""

    key = ("<=95" if ltv <= 95 else ">95") + "_" + ("<=15" if term_years <= 15 else ">15")
    return table.get(key, 0.55)


def va_funding_fee_pct(first_use, down_pct, table):
    """Funding fee percentage for VA loans based on usage and down payment."""

    if first_use:
        if down_pct >= 10:
            return table.get("first_10+", 1.25)
        if down_pct >= 5:
            return table.get("first_5_10", 1.50)
        return table.get("first_0_5", 2.15)
    else:
        if down_pct >= 10:
            return table.get("subseq_10+", 1.25)
        if down_pct >= 5:
            return table.get("subseq_5_10", 1.50)
        return table.get("subseq_0_5", 3.30)


def usda_guarantee_pct(table):
    """USDA upfront guarantee fee percentage."""

    return table.get("guarantee_pct", 1.0)


def usda_annual_fee_pct(table):
    """USDA annual fee percentage added to the monthly payment."""

    return table.get("annual_pct", 0.35)

def apply_program_fees(
    program,
    purchase_price,
    base_loan,
    dp_amt,
    rate_pct,
    term_years,
    conv_mi_tbl,
    fha_tables,
    va_tbl,
    usda_tbl,
    finance_upfront,
    first_use_va,
    fico_bucket,
):
    """Calculate adjusted loan amounts and mortgage insurance by program."""

    ltv = compute_ltv(purchase_price, base_loan)
    down_pct = 100.0 * nz(dp_amt) / nz(purchase_price) if nz(purchase_price) else 0.0
    if program == "Conventional":
        mi_ann_pct = conventional_mi_factor(ltv, fico_bucket, conv_mi_tbl)
        mi_monthly = base_loan * (mi_ann_pct / 100) / 12
        return {"adjusted_loan": base_loan, "mi_monthly": mi_monthly, "upfront_amt": 0.0, "ltv": ltv}
    if program == "FHA":
        uf_pct = fha_tables.get("ufmip_pct", 1.75)
        ann_pct = fha_mip_factor(ltv, term_years, fha_tables.get("annual_table", {}))
        upfront = base_loan * (uf_pct / 100)
        adj = base_loan + upfront if finance_upfront else base_loan
        ltv_calc = compute_ltv(purchase_price, adj) if finance_upfront else ltv
        mi_monthly = adj * (ann_pct / 100) / 12
        return {"adjusted_loan": adj, "mi_monthly": mi_monthly, "upfront_amt": upfront, "ltv": ltv_calc}
    if program == "VA":
        fee_pct = va_funding_fee_pct(first_use_va, down_pct, va_tbl)
        upfront = base_loan * (fee_pct / 100)
        adj = base_loan + upfront if finance_upfront else base_loan
        ltv_calc = compute_ltv(purchase_price, adj) if finance_upfront else ltv
        return {"adjusted_loan": adj, "mi_monthly": 0.0, "upfront_amt": upfront, "ltv": ltv_calc}
    if program == "USDA":
        g_pct = usda_guarantee_pct(usda_tbl)
        upfront = base_loan * (g_pct / 100)
        adj = base_loan + upfront if finance_upfront else base_loan
        ann_pct = usda_annual_fee_pct(usda_tbl)
        mi_monthly = adj * (ann_pct / 100) / 12
        ltv_calc = compute_ltv(purchase_price, adj) if finance_upfront else ltv
        return {"adjusted_loan": adj, "mi_monthly": mi_monthly, "upfront_amt": upfront, "ltv": ltv_calc}
    return {"adjusted_loan": base_loan, "mi_monthly": 0.0, "upfront_amt": 0.0, "ltv": ltv}


def piti_components(
    program,
    purchase_price,
    base_loan,
    rate_pct,
    term_years,
    tax_rate_pct,
    hoi_annual,
    hoa_monthly,
    conv_mi_tbl,
    fha_tables,
    va_tbl,
    usda_tbl,
    finance_upfront,
    first_use_va,
    fico_bucket,
):
    """Break PITI into components including mortgage insurance and fees."""

    adj = apply_program_fees(
        program,
        purchase_price,
        base_loan,
        purchase_price - base_loan,
        rate_pct,
        term_years,
        conv_mi_tbl,
        fha_tables,
        va_tbl,
        usda_tbl,
        finance_upfront,
        first_use_va,
        fico_bucket,
    )
    pi = monthly_payment(adj["adjusted_loan"], rate_pct, term_years)
    taxes = nz(purchase_price) * nz(tax_rate_pct) / 100 / 12
    hoi = nz(hoi_annual) / 12
    hoa = nz(hoa_monthly)
    total = pi + taxes + hoi + hoa + adj["mi_monthly"]
    return {
        "pi": pi,
        "taxes": taxes,
        "hoi": hoi,
        "hoa": hoa,
        "mi": adj["mi_monthly"],
        "total": total,
        "adjusted_loan": adj["adjusted_loan"],
        "ltv": adj["ltv"],
        "upfront_amt": adj["upfront_amt"],
    }


def dti(front_housing, all_liabilities, total_income):
    """Return front‑end and back‑end debt‑to‑income ratios."""

    inc = nz(total_income)
    fe = 0.0 if inc == 0 else nz(front_housing) / inc
    be = 0.0 if inc == 0 else nz(all_liabilities) / inc
    return fe, be


def max_affordable_pi(
    total_income,
    other_liabilities,
    taxes_ins_hoa_mi,
    target_fe_pct,
    target_be_pct,
):
    """Maximum principal & interest payment given DTI targets."""

    inc = nz(total_income)
    fe_max = max(0.0, inc * nz(target_fe_pct) / 100 - nz(taxes_ins_hoa_mi))
    be_max = max(0.0, inc * nz(target_be_pct) / 100 - nz(other_liabilities))
    return fe_max, be_max, min(fe_max, be_max)


def max_qualifying_loan(
    total_income,
    other_liabilities,
    taxes_ins_hoa_mi,
    target_fe_pct,
    target_be_pct,
    rate_pct,
    term_years,
    down_payment_amt,
    program,
    conv_mi_tbl,
    fha_tables,
    va_tbl,
    usda_tbl,
    finance_upfront,
    first_use_va,
    fico_bucket,
    iterations: int = 20,
):
    """Solve for maximum loan amount given DTI targets and cash to close."""

    fe_max, be_max, pi_allowed = max_affordable_pi(
        total_income, other_liabilities, taxes_ins_hoa_mi, target_fe_pct, target_be_pct
    )
    if pi_allowed <= 0:
        return {
            "max_pi": 0.0,
            "base_loan": 0.0,
            "adjusted_loan": 0.0,
            "purchase_price": down_payment_amt,
        }

    adj_limit = principal_from_payment(pi_allowed, rate_pct, term_years)
    low, high = 0.0, adj_limit
    for _ in range(iterations):
        mid = (low + high) / 2
        fees = apply_program_fees(
            program,
            mid + down_payment_amt,
            mid,
            down_payment_amt,
            rate_pct,
            term_years,
            conv_mi_tbl,
            fha_tables,
            va_tbl,
            usda_tbl,
            finance_upfront,
            first_use_va,
            fico_bucket,
        )
        if fees["adjusted_loan"] > adj_limit:
            high = mid
        else:
            low = mid
    base = low
    purchase_price = base + down_payment_amt
    fees = apply_program_fees(
        program,
        purchase_price,
        base,
        down_payment_amt,
        rate_pct,
        term_years,
        conv_mi_tbl,
        fha_tables,
        va_tbl,
        usda_tbl,
        finance_upfront,
        first_use_va,
        fico_bucket,
    )
    return {
        "max_pi": pi_allowed,
        "base_loan": base,
        "adjusted_loan": fees["adjusted_loan"],
        "purchase_price": purchase_price,
    }
