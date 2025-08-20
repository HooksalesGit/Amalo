
import json, io
import streamlit as st
import pandas as pd
from core.presets import PROGRAM_PRESETS, CONV_MI_BANDS, FHA_TABLES, VA_TABLE, USDA_TABLE, DISCLAIMER, FL_DEFAULTS
from core.calculators import (
    w2_totals, sch_c_totals, k1_totals, ccorp_totals, rentals_policy, other_income_totals,
    combine_income, piti_components, dti, max_affordable_pi, monthly_payment, principal_from_payment, nz
)
from core.rules import evaluate_rules, has_blocking
from core.pdf_export import build_prequal_pdf

st.set_page_config(page_title="Mortgage Income & DTI Dashboard", layout="wide")

def init_state():
    ss = st.session_state
    ss.setdefault("num_borrowers", 2)
    ss.setdefault("program", "Conventional")
    ss.setdefault("targets", PROGRAM_PRESETS["Conventional"].copy())
    ss.setdefault("fico_bucket", ">=740")
    ss.setdefault("program_tables", {
        "conventional_mi": CONV_MI_BANDS.copy(),
        "fha": FHA_TABLES.copy(),
        "va": VA_TABLE.copy(),
        "usda": USDA_TABLE.copy()
    })
    ss.setdefault("finance_upfront", True)
    ss.setdefault("first_use_va", True)
    ss.setdefault("rental_method", "ScheduleE")
    ss.setdefault("subject_market_rent", 0.0)
    ss.setdefault("k1_verified_distributions", False)
    ss.setdefault("k1_analyzed_liquidity", False)
    ss.setdefault("support_continuance_ok", False)
    ss.setdefault("borrower_names", {1:"Borrower 1", 2:"Borrower 2"})
    def mkdf(cols): return pd.DataFrame(columns=cols)
    ss.setdefault("w2", mkdf(['BorrowerID','Employer','PayType','AnnualSalary','HourlyRate','HoursPerWeek','OT_YTD','Bonus_YTD','Comm_YTD','Months_YTD','OT_LY','Bonus_LY','Comm_LY','Months_LY','IncludeVariable']))
    ss.setdefault("schc", mkdf(['BorrowerID','BusinessName','Year','NetProfit','Nonrecurring','Depletion','Depreciation','NonDedMeals','UseOfHome','AmortCasualty','BusinessMiles','MileDepRate']))
    ss.setdefault("k1", mkdf(['BorrowerID','EntityName','Type','Year','OwnershipPct','Ordinary','NetRentalOther','GuaranteedPmt','Nonrecurring','Depreciation','Depletion','AmortCasualty','NotesLT1yr','NonDed_TandE']))
    ss.setdefault("c1120", mkdf(['BorrowerID','CorpName','Year','OwnershipPct','TaxableIncome','TotalTax','Nonrecurring','OtherIncLoss','Depreciation','Depletion','AmortCasualty','NotesLT1yr','NonDed_TandE','DividendsPaid']))
    ss.setdefault("rentals", mkdf(['BorrowerID','Property','Year','Rents','Expenses','Depreciation']))
    ss.setdefault("other", mkdf(['BorrowerID','Type','GrossMonthly','GrossUpPct']))
    ss.setdefault("debts", mkdf(['DebtName','MonthlyPayment']))
    ss.setdefault("housing", {
        "purchase_price": 500000.0, "down_payment_amt": 100000.0,
        "rate_pct": 6.75, "term_years": 30,
        "tax_rate_pct": FL_DEFAULTS["tax_rate_pct"],
        "hoi_annual": FL_DEFAULTS["hoi_annual"], "hoa_monthly": 0.0
    })
    ss.setdefault("override_reason", "")

init_state()

with st.sidebar:
    st.header("Program & Targets")
    st.session_state.program = st.selectbox("Program", list(PROGRAM_PRESETS.keys()) + ["Jumbo"])
    if st.button("Apply Program Presets"):
        preset = PROGRAM_PRESETS.get(st.session_state.program, PROGRAM_PRESETS["Conventional"])
        st.session_state.targets.update(preset)
    c_t = st.columns(2)
    st.session_state.targets['FE'] = c_t[0].number_input("Target Front-End DTI %", value=float(st.session_state.targets['FE']), step=0.5)
    st.session_state.targets['BE'] = c_t[1].number_input("Target Back-End DTI %", value=float(st.session_state.targets['BE']), step=0.5)

    st.header("Borrowers")
    st.session_state.num_borrowers = st.number_input("Number of Borrowers", min_value=1, max_value=6, value=int(st.session_state.num_borrowers), step=1)
    with st.expander("Borrower Names"):
        for i in range(1, st.session_state.num_borrowers+1):
            st.session_state.borrower_names[i] = st.text_input(f"Borrower {i} name", value=st.session_state.borrower_names.get(i, f"Borrower {i}"))

    st.header("MI / MIP / Fees")
    st.session_state.fico_bucket = st.selectbox("FICO Bucket (display only)", [">=740","720-739","700-719","660-699","620-659","<620"])
    with st.expander("Conventional MI Bands (annual %) by LTV"):
        df = pd.DataFrame([{"Band":k,"AnnualPct":v} for k,v in st.session_state.program_tables['conventional_mi'].items()])
        df = st.data_editor(df, use_container_width=True)
        st.session_state.program_tables['conventional_mi'] = dict(zip(df['Band'], df['AnnualPct']))
    with st.expander("FHA Factors"):
        cols = st.columns(2)
        st.session_state.program_tables['fha']['ufmip_pct'] = cols[0].number_input("Upfront MIP (%)", value=float(st.session_state.program_tables['fha'].get('ufmip_pct',1.75)), step=0.05)
        tbl = st.session_state.program_tables['fha'].get('annual_table', {})
        df = pd.DataFrame([{"Key":k,"AnnualPct":v} for k,v in tbl.items()])
        df = st.data_editor(df, use_container_width=True)
        st.session_state.program_tables['fha']['annual_table'] = {r['Key']:r['AnnualPct'] for _,r in df.iterrows()}
    with st.expander("VA Funding Fee Table (%)"):
        st.session_state.first_use_va = st.checkbox("First Use", value=bool(st.session_state.first_use_va))
        va = st.session_state.program_tables['va']
        df = pd.DataFrame([{"Key":k,"Pct":v} for k,v in va.items()])
        df = st.data_editor(df, use_container_width=True)
        st.session_state.program_tables['va'] = {r['Key']:r['Pct'] for _,r in df.iterrows()}
    with st.expander("USDA Guarantee & Annual (%)"):
        usda = st.session_state.program_tables['usda']
        c = st.columns(2)
        usda['guarantee_pct'] = c[0].number_input("Guarantee Fee (%)", value=float(usda.get('guarantee_pct',1.0)), step=0.05)
        usda['annual_pct'] = c[1].number_input("Annual Fee (%)", value=float(usda.get('annual_pct',0.35)), step=0.05)

    st.header("Upfront Fees")
    st.session_state.finance_upfront = st.checkbox("Finance upfront fee (if applicable)", value=bool(st.session_state.finance_upfront))

    st.header("Save / Load")
    save_btn = st.button("Download Session JSON")
    up = st.file_uploader("Load Session JSON", type="json")
    if save_btn:
        snapshot = {k:v for k,v in st.session_state.items() if k not in ['forms']}
        st.download_button("Download JSON", data=json.dumps(snapshot, default=str), file_name="session_export.json", mime="application/json")
    if up is not None:
        try:
            payload = json.loads(up.read())
            for k,v in payload.items(): st.session_state[k] = v
            st.success("Session loaded.")
        except Exception as e:
            st.error(f"Failed to load: {e}")

st.title("Mortgage Income & DTI Dashboard")
st.caption("Florida-friendly defaults • Program-aware calculations • Guardrails & warnings • Exports")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "W‑2 / Base", "Sch C (1040)","K‑1 (1065/1120S)","1120 C‑Corp","Rentals (Sch E)","Other Income",
    "Payment & Housing","Other Debts","Dashboard","Max Qualifiers"
])

with tab1:
    st.subheader("W‑2 / Base Employment")
    st.write("Use IncludeVariable=1 when variable income is stable (YTD + LY / months).")
    st.session_state.w2 = st.data_editor(st.session_state.w2, num_rows="dynamic", use_container_width=True)

with tab2:
    st.subheader("Self‑Employed — Schedule C (two-year analysis)")
    st.session_state.schc = st.data_editor(st.session_state.schc, num_rows="dynamic", use_container_width=True)

with tab3:
    st.subheader("Partnerships & S Corps — K‑1")
    c1,c2 = st.columns(2)
    st.session_state.k1_verified_distributions = c1.checkbox("Verified distributions history")
    st.session_state.k1_analyzed_liquidity = c2.checkbox("Analyzed business liquidity (if no distributions)")
    st.session_state.k1 = st.data_editor(st.session_state.k1, num_rows="dynamic", use_container_width=True)

with tab4:
    st.subheader("Regular Corporation — 1120 (100% owner only)")
    st.warning("Only include entities where the borrower owns 100%. The app filters 1120 entries to >=100%.")
    st.session_state.c1120 = st.data_editor(st.session_state.c1120, num_rows="dynamic", use_container_width=True)

with tab5:
    st.subheader("Rental Income — Policy")
    st.session_state.rental_method = st.radio("Method", ["ScheduleE","SeventyFivePctGross"], horizontal=True)
    st.session_state.subject_market_rent = st.number_input("Subject Market Rent (if applicable)", value=float(st.session_state.subject_market_rent), step=50.0)
    st.session_state.rentals = st.data_editor(st.session_state.rentals, num_rows="dynamic", use_container_width=True)

with tab6:
    st.subheader("Other Qualifying Income")
    st.session_state.other = st.data_editor(st.session_state.other, num_rows="dynamic", use_container_width=True)
    st.session_state.support_continuance_ok = st.checkbox("Support income (if any) has ≥3 years continuance")

with tab7:
    st.subheader("Payment & Proposed Housing (Program‑Aware)")
    H = st.session_state.housing
    c1,c2,c3 = st.columns(3)
    H['purchase_price'] = c1.number_input("Purchase Price ($)", value=float(H['purchase_price']), step=1000.0)
    H['down_payment_amt'] = c2.number_input("Down Payment Amount ($)", value=float(H['down_payment_amt']), step=1000.0)
    H['rate_pct'] = c3.number_input("Interest Rate (%)", value=float(H['rate_pct']), step=0.125)
    c4,c5,c6 = st.columns(3)
    H['term_years'] = c4.number_input("Term (years)", value=int(H['term_years']), step=5)
    H['tax_rate_pct'] = c5.number_input("Property Tax Rate (%)", value=float(H['tax_rate_pct']), step=0.05)
    H['hoi_annual'] = c6.number_input("Homeowners Insurance (Annual $)", value=float(H['hoi_annual']), step=50.0)
    c7,c8 = st.columns(2)
    H['hoa_monthly'] = c7.number_input("HOA/Condo Dues (Monthly $)", value=float(H['hoa_monthly']), step=10.0)
    dp_amt = float(H['down_payment_amt'])
    base_loan = max(0.0, float(H['purchase_price']) - dp_amt)
    conv_tbl = st.session_state.program_tables['conventional_mi']
    fha_tbls = st.session_state.program_tables['fha']
    va_tbl = st.session_state.program_tables['va']
    usda_tbl = st.session_state.program_tables['usda']
    fees = piti_components(
        st.session_state.program, H['purchase_price'], base_loan, H['rate_pct'], H['term_years'],
        H['tax_rate_pct'], H['hoi_annual'], H['hoa_monthly'],
        conv_tbl, fha_tbls, va_tbl, usda_tbl,
        st.session_state.finance_upfront, st.session_state.first_use_va, st.session_state.fico_bucket
    )
    st.write(f"**Base Loan (before upfront):** ${base_loan:,.0f}")
    st.write(f"**Adjusted Loan (after financed fee if applicable):** ${fees['adjusted_loan']:,.0f}")
    st.write(f"**LTV (base): {fees['ltv']:.2f}%**")
    st.write(f"**P&I:** ${fees['pi']:,.2f} | **Taxes:** ${fees['taxes']:,.2f} | **HOI:** ${fees['hoi']:,.2f} | **HOA:** ${fees['hoa']:,.2f} | **MI/MIP/Annual:** ${fees['mi']:,.2f}")
    st.write(f"**Proposed Housing (PITI + HOA + MI): ${fees['total']:,.2f}**")
    if fees['upfront_amt'] > 0 and st.session_state.finance_upfront:
        st.caption(f"Upfront financed: ${fees['upfront_amt']:,.2f}")

with tab8:
    st.subheader("Other Recurring Debts")
    st.session_state.debts = st.data_editor(st.session_state.debts, num_rows="dynamic", use_container_width=True)

with tab9:
    st.subheader("DTI, Warnings & Checklist")
    rentals_df = rentals_policy(
        st.session_state.rentals, method=st.session_state.rental_method,
        subject_pitia=fees['total'], subject_market_rent=st.session_state.subject_market_rent
    )
    incomes = combine_income(
        st.session_state.num_borrowers,
        st.session_state.w2, st.session_state.schc, st.session_state.k1,
        st.session_state.c1120, rentals_df, st.session_state.other
    )
    st.dataframe(incomes, use_container_width=True)
    total_income = incomes['TotalMonthlyIncome'].sum() if not incomes.empty else 0.0
    other_debts = 0.0 if st.session_state.debts.empty else pd.to_numeric(st.session_state.debts['MonthlyPayment'], errors='coerce').fillna(0.0).sum()
    FE, BE = dti(fees['total'], fees['total'] + other_debts, total_income)
    cols = st.columns(4)
    cols[0].metric("Total Monthly Income", f"${total_income:,.2f}")
    cols[1].metric("Housing (PITIA)", f"${fees['total']:,.2f}")
    cols[2].metric("Other Debts", f"${other_debts:,.2f}")
    cols[3].metric("All Liabilities", f"${fees['total'] + other_debts:,.2f}")
    cols = st.columns(4)
    cols[0].metric("Front-End DTI", f"{FE*100:.2f}%", delta="PASS" if (FE*100) <= float(st.session_state.targets['FE']) else "CHECK")
    cols[1].metric("Back-End DTI", f"{BE*100:.2f}%", delta="PASS" if (BE*100) <= float(st.session_state.targets['BE']) else "CHECK")
    cols[2].metric("Target FE", f"{st.session_state.targets['FE']:.2f}%")
    cols[3].metric("Target BE", f"{st.session_state.targets['BE']:.2f}%")
    w2_included_lt_12=False
    if not st.session_state.w2.empty:
        months = pd.to_numeric(st.session_state.w2['Months_YTD'], errors='coerce').fillna(0) + pd.to_numeric(st.session_state.w2['Months_LY'], errors='coerce').fillna(0)
        included = pd.to_numeric(st.session_state.w2['IncludeVariable'], errors='coerce').fillna(0) == 1
        if any((months < 12) & included): w2_included_lt_12=True
    w2_declining_flag = bool(incomes.get('AnyDecliningFlag', pd.Series([False])).any())
    schc_declining = bool(incomes.get('SchC_DecliningFlag', pd.Series([False])).any())
    uses_k1 = not st.session_state.k1.empty
    uses_c1120 = not st.session_state.c1120.empty
    c1120_any_lt_100 = False
    if uses_c1120:
        own = pd.to_numeric(st.session_state.c1120['OwnershipPct'], errors='coerce').fillna(0)
        c1120_any_lt_100 = any(own < 100)
    uses_support_income = any(st.session_state.other['Type'].astype(str).str.lower().str.contains("alimony|child", regex=True)) if not st.session_state.other.empty else False
    rental_method_conflict = False
    sanity_inputs_out_of_band = False
    if st.session_state.housing['purchase_price'] > 0:
        annual_non_PI = (fees['taxes'] + fees['hoi'] + fees['hoa'] + fees['mi']) * 12
        if annual_non_PI > 0.05 * st.session_state.housing['purchase_price']:
            sanity_inputs_out_of_band = True
    rule_state = {
        "total_income": total_income,
        "FE": FE, "BE": BE,
        "target_FE": st.session_state.targets['FE'], "target_BE": st.session_state.targets['BE'],
        "w2_meta": {"var_included_lt_12": w2_included_lt_12, "declining_var": w2_declining_flag},
        "schc_declining": schc_declining,
        "uses_k1": uses_k1,
        "k1_verified_distributions": st.session_state.k1_verified_distributions,
        "k1_analyzed_liquidity": st.session_state.k1_analyzed_liquidity,
        "uses_c1120": uses_c1120,
        "c1120_any_lt_100": c1120_any_lt_100,
        "uses_support_income": uses_support_income,
        "support_continuance_ok": st.session_state.support_continuance_ok,
        "rental_method_conflict": rental_method_conflict,
        "sanity_inputs_out_of_band": sanity_inputs_out_of_band,
    }
    rule_results = evaluate_rules(rule_state)
    if rule_results:
        for r in rule_results:
            if r.severity == "critical":
                st.error(f"[{r.code}] {r.message}")
            elif r.severity == "warn":
                st.warning(f"[{r.code}] {r.message}")
            else:
                st.info(f"[{r.code}] {r.message}")
    else:
        st.success("No warnings.")
    st.divider()
    checklist = []
    if not st.session_state.w2.empty:
        checklist += [{"label":"Most recent paystubs (30 days)","checked":False},
                      {"label":"W-2s (2 years)","checked":False},
                      {"label":"VOE (verbal/written)","checked":False}]
    if not st.session_state.schc.empty or not st.session_state.k1.empty or not st.session_state.c1120.empty:
        checklist += [{"label":"Personal tax returns (2 years)","checked":False},
                      {"label":"Business returns (K-1/1065/1120S/1120)","checked":False}]
    if st.session_state.k1_verified_distributions or st.session_state.k1_analyzed_liquidity:
        checklist += [{"label":"K-1 distributions evidence or business liquidity analysis","checked":True}]
    if not st.session_state.rentals.empty:
        checklist += [{"label":"Leases / Market rent report","checked":False},
                      {"label":"Schedule E pages","checked":False}]
    if uses_support_income:
        checklist += [{"label":"Court order + proof of receipt + ≥3 years continuance","checked":st.session_state.support_continuance_ok}]
    if not st.session_state.other.empty:
        checklist += [{"label":"Evidence of receipt/continuance for other income","checked":False}]
    if not checklist:
        checklist = [{"label":"Standard disclosures","checked":False}]
    st.write("**Documentation Checklist**")
    for i, item in enumerate(checklist):
        checklist[i]["checked"] = st.checkbox(item["label"], value=item["checked"], key=f"chk_{i}")
    st.divider()
    st.write("**Disclaimer**")
    st.caption(DISCLAIMER)
    st.divider()
    c1, c2, c3 = st.columns([2,1,1])
    blocking = has_blocking(rule_results)
    if blocking:
        st.error("Critical warnings present. Provide an override reason to enable PDF export.")
        st.session_state.override_reason = c1.text_input("Override reason (will be embedded in PDF)", value=st.session_state.override_reason)
    else:
        st.session_state.override_reason = ""
    def make_csv_bytes():
        buf = io.StringIO()
        summary = pd.DataFrame([{
            "Program": st.session_state.program,
            "PurchasePrice": st.session_state.housing['purchase_price'],
            "DownPayment": st.session_state.housing['down_payment_amt'],
            "AdjustedLoan": fees['adjusted_loan'],
            "P&I": fees['pi'],
            "Taxes": fees['taxes'],
            "HOI": fees['hoi'],
            "HOA": fees['hoa'],
            "MI_MIP": fees['mi'],
            "HousingTotal": fees['total'],
            "TotalIncome": total_income,
            "OtherDebts": other_debts,
            "FrontEndDTI_pct": FE*100,
            "BackEndDTI_pct": BE*100,
            "Targets_FE_BE": f"{st.session_state.targets['FE']}/{st.session_state.targets['BE']}"
        }])
        summary.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")
    st.download_button("Download CSV Summary", data=make_csv_bytes(), file_name="prequal_summary.csv", mime="text/csv")
    if (not blocking) or (blocking and st.session_state.override_reason.strip()):
        if c2.button("Export Prequal PDF"):
            path = "prequal_summary.pdf"
            header = ["Borrower"] + [c for c in ["W2","SchC","K1","1120","Rental","Other","Total"]]
            rows = [header]
            for _, row in incomes.iterrows():
                bid = int(row['BorrowerID']); name = st.session_state.borrower_names.get(bid, f"Borrower {bid}")
                rows.append([name,
                    f"${row['W2_Monthly']:,.2f}", f"${row['SchC_Monthly']:,.2f}", f"${row['K1_Monthly']:,.2f}",
                    f"${row['C1120_Monthly']:,.2f}", f"${row['Rental_Monthly']:,.2f}", f"${row['Other_Monthly']:,.2f}",
                    f"${row['TotalMonthlyIncome']:,.2f}"
                ])
            warn_export = [{"code":r.code, "severity":r.severity, "message": r.message} for r in rule_results]
            if st.session_state.override_reason.strip():
                warn_export.append({"code":"OVERRIDE", "severity":"info", "message":f"Override reason: {st.session_state.override_reason.strip()}"})
            snapshot = {
                "deal_snapshot": {
                    "Program": st.session_state.program,
                    "Rate / Term": f"{st.session_state.housing['rate_pct']}% / {st.session_state.housing['term_years']} yrs",
                    "Purchase Price": f"${st.session_state.housing['purchase_price']:,.0f}",
                    "Down Payment": f"${st.session_state.housing['down_payment_amt']:,.0f}",
                    "LTV (base)": f"{fees['ltv']:.2f}%",
                    "Financed Upfront?": "Yes" if st.session_state.finance_upfront else "No"
                },
                "totals": {
                    "P&I": f"${fees['pi']:,.2f}",
                    "Taxes": f"${fees['taxes']:,.2f}",
                    "HOI": f"${fees['hoi']:,.2f}",
                    "HOA": f"${fees['hoa']:,.2f}",
                    "MI/MIP": f"${fees['mi']:,.2f}",
                    "Housing (PITIA)": f"${fees['total']:,.2f}",
                    "Total Income": f"${total_income:,.2f}",
                    "Front-End DTI": f"{FE*100:.2f}%",
                    "Back-End DTI": f"{BE*100:.2f}%",
                    "Targets (FE/BE)": f"{st.session_state.targets['FE']}% / {st.session_state.targets['BE']}%"
                }
            }
            branding = {"title":"Prequalification Summary","mlo":", ".join(n for n in st.session_state.borrower_names.values() if n), "contact":"", "nmls":""}
            build_prequal_pdf(path, branding, snapshot, rows, warn_export, checklist)
            with open(path, "rb") as f:
                st.download_button("Download PDF", data=f.read(), file_name="prequal_summary.pdf", mime="application/pdf")
    else:
        c3.info("Resolve critical warnings or add an override reason to enable PDF export.")

with tab10:
    st.subheader("Max Purchase / Max Loan Solver")
    try:
        incomes = combine_income(
            st.session_state.num_borrowers,
            st.session_state.w2, st.session_state.schc, st.session_state.k1,
            st.session_state.c1120, rentals_policy(st.session_state.rentals, st.session_state.rental_method, st.session_state.subject_market_rent), st.session_state.other
        )
        total_income = incomes['TotalMonthlyIncome'].sum()
    except Exception:
        total_income = 0.0
    rate = st.number_input("Rate (%)", value=float(st.session_state.housing['rate_pct']), step=0.125, key="solver_rate")
    term = st.number_input("Term (years)", value=int(st.session_state.housing['term_years']), step=5, key="solver_term")
    taxes_ins_hoa_mi = st.number_input("Taxes + Insurance + HOA + MI (monthly)", value=0.0, step=25.0)
    other_debts = 0.0 if st.session_state.debts.empty else pd.to_numeric(st.session_state.debts['MonthlyPayment'], errors='coerce').fillna(0.0).sum()
    targets = st.session_state.targets
    fe_max, be_max, conservative_pi = max_affordable_pi(total_income, other_debts, taxes_ins_hoa_mi, targets['FE'], targets['BE'])
    max_loan = principal_from_payment(conservative_pi, rate, term)
    dp_pct = st.number_input("Down Payment %", value=20.0, step=1.0)
    max_purchase = max_loan / (1 - dp_pct/100.0) if dp_pct < 100 else max_loan
    c1,c2,c3 = st.columns(3)
    c1.metric("Conservative Max P&I", f"${conservative_pi:,.2f}")
    c2.metric("Max Base Loan", f"${max_loan:,.0f}")
    c3.metric("Max Purchase (given DP%)", f"${max_purchase:,.0f}")

st.sidebar.caption(DISCLAIMER)
