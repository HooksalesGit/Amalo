
DISCLAIMER = (
    "This tool implements common calculations aligned with agency/investor practices "
    "(e.g., FNMA-style self-employed analyses, K‑1 distribution/liquidity checks, and program-aware MI/MIP/funding fees). "
    "Results are estimates only; AUS findings, lender overlays, and underwriter discretion prevail. "
    "Income used must be stable and well documented—demonstrate continuance, trends, and business liquidity as applicable."
)

PROGRAM_PRESETS = {"Conventional":{"FE":31.0,"BE":45.0},"FHA":{"FE":31.0,"BE":50.0},
"VA":{"FE":35.0,"BE":50.0},"USDA":{"FE":29.0,"BE":41.0},"Jumbo":{"FE":35.0,"BE":43.0}}

CONV_MI_BANDS = {">=97":0.90,"95-97":0.62,"90-95":0.40,"85-90":0.25,"<85":0.00}
FHA_TABLES = {"ufmip_pct":1.75,"annual_table":{"<=95_<=15":0.15,"<=95_>15":0.50,">95_<=15":0.40,">95_>15":0.55}}
VA_TABLE = {"first_0_5":2.15,"first_5_10":1.50,"first_10+":1.25,"subseq_0_5":3.30,"subseq_5_10":1.50,"subseq_10+":1.25}
USDA_TABLE = {"guarantee_pct":1.0,"annual_pct":0.35}
FL_DEFAULTS = {"tax_rate_pct":1.25,"hoi_annual":1800.0,"mi_annual_pct":0.60}
