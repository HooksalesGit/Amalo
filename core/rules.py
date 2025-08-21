
from __future__ import annotations
from typing import Literal, List, Dict, Any
from pydantic import BaseModel, Field

class RuleResult(BaseModel):
    code: str
    severity: Literal["info","warn","critical"]
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)

def evaluate_rules(state: dict) -> List[RuleResult]:
    res: List[RuleResult] = []
    total_income=float(state.get("total_income",0.0))
    FE=float(state.get("FE",0.0))*100; BE=float(state.get("BE",0.0))*100
    target_FE=float(state.get("target_FE",31.0)); target_BE=float(state.get("target_BE",45.0))

    w2_meta=state.get("w2_meta",{})
    if w2_meta.get("var_included_lt_12", False):
        res.append(
            RuleResult(
                code="W2_VAR_LT_12",
                severity="warn",
                message="Variable W‑2 income included with <12 months history.",
            )
        )
    if w2_meta.get("declining_var", False):
        res.append(
            RuleResult(
                code="W2_VAR_DECLINE",
                severity="warn",
                message="Potentially declining W‑2 variable income.",
            )
        )
    if w2_meta.get("declining_base", False):
        res.append(
            RuleResult(
                code="W2_BASE_DECLINE",
                severity="warn",
                message="Potentially declining W‑2 base income.",
            )
        )

    if state.get("schc_declining", False):
        res.append(
            RuleResult(
                code="SCHC_DECLINE",
                severity="warn",
                message="Schedule C year‑over‑year decline >20%.",
            )
        )

    if state.get("k1_declining", False):
        res.append(
            RuleResult(
                code="K1_DECLINE",
                severity="warn",
                message="K‑1 income declining year‑over‑year.",
            )
        )

    if state.get("c1120_declining", False):
        res.append(
            RuleResult(
                code="C1120_DECLINE",
                severity="warn",
                message="1120 income declining year‑over‑year.",
            )
        )

    if state.get("rental_declining", False):
        res.append(
            RuleResult(
                code="RENTAL_DECLINE",
                severity="warn",
                message="Rental income declining year‑over‑year.",
            )
        )

    if state.get("uses_k1", False) and not (
        state.get("k1_verified_distributions", False)
        or state.get("k1_analyzed_liquidity", False)
    ):
        res.append(
            RuleResult(
                code="K1_DIST_LIQ",
                severity="critical",
                message="K‑1 used but distributions/liquidity not verified.",
            )
        )

    if state.get("uses_c1120", False) and state.get("c1120_any_lt_100", False):
        res.append(
            RuleResult(
                code="C1120_OWN_LT_100",
                severity="critical",
                message="1120 income must be 100% owner to count.",
            )
        )

    if state.get("uses_support_income", False) and not state.get(
        "support_continuance_ok", False
    ):
        res.append(
            RuleResult(
                code="CONTINUANCE_REQ",
                severity="critical",
                message="Support income requires ≥3 years continuance.",
            )
        )

    if state.get("rental_method_conflict", False):
        res.append(
            RuleResult(
                code="RENTAL_METHOD_CONFLICT",
                severity="warn",
                message="Choose either Schedule E or 75% of Gross, not both.",
            )
        )

    if total_income <= 0:
        res.append(
            RuleResult(
                code="NO_INCOME",
                severity="critical",
                message="No income entered; DTI is not meaningful.",
            )
        )

    if FE > target_FE or BE > target_BE:
        res.append(
            RuleResult(
                code="DTI_OVER_TARGET",
                severity="warn",
                message="DTI exceeds target thresholds.",
            )
        )

    if state.get("sanity_inputs_out_of_band", False):
        res.append(
            RuleResult(
                code="SANITY_HOA_TAX_MI",
                severity="info",
                message="Inputs appear out of typical ranges for purchase price.",
            )
        )

    return res

def has_blocking(res: List[RuleResult]) -> bool:
    return any(r.severity=="critical" for r in res)
