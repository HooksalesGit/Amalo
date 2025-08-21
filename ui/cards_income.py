import copy
import streamlit as st
from core.models import W2, SchC, K1, C1120, Rental, OtherIncome

INCOME_MODELS = {
    "w2": ("W-2", W2),
    "schc": ("Schedule C", SchC),
    "k1": ("K-1", K1),
    "c1120": ("1120", C1120),
    "rental": ("Rental", Rental),
    "other": ("Other", OtherIncome),
}


def _default_payload(t: str) -> dict:
    return INCOME_MODELS[t][1]().model_dump()


def _monthly_preview(card: dict) -> float:
    p = card.get("payload", {})
    t = card.get("type")
    if t == "w2":
        return float(p.get("AnnualSalary", 0)) / 12.0
    if t == "other":
        return float(p.get("GrossMonthly", 0))
    return float(p.get("QualMonthly", 0))


def render_income_cards() -> float:
    st.session_state.setdefault("income_cards", [])
    if st.button("Add Income Card", key="add_income_card"):
        st.session_state.income_cards.append({"type": "w2", "payload": _default_payload("w2")})
    total = 0.0
    for idx, card in enumerate(list(st.session_state.income_cards)):
        label = INCOME_MODELS[card["type"]][0]
        with st.expander(f"Income #{idx+1} — {label}"):
            sel = st.selectbox(
                "Type",
                list(INCOME_MODELS.keys()),
                format_func=lambda k: INCOME_MODELS[k][0],
                index=list(INCOME_MODELS.keys()).index(card["type"]),
                key=f"inc_type_{idx}",
            )
            if sel != card["type"]:
                card["type"] = sel
                card["payload"] = _default_payload(sel)
            payload = card["payload"]
            model_cls = INCOME_MODELS[card["type"]][1]
            items = list(payload.items())
            for i in range(0, len(items), 2):
                cols = st.columns(2)
                for col_idx, (f, v) in enumerate(items[i : i + 2]):
                    with cols[col_idx]:
                        st.markdown(f"**{f}**")
                        desc = ""
                        try:
                            desc = model_cls.model_fields[f].description or ""
                        except Exception:
                            pass
                        if not desc:
                            desc = f"Enter {f.replace('_', ' ')}"
                        st.caption(desc)
                        if isinstance(v, (int, float)):
                            payload[f] = st.number_input("", value=float(v), key=f"inc_{idx}_{f}")
                        else:
                            payload[f] = st.text_input("", value=v, key=f"inc_{idx}_{f}")
            preview = _monthly_preview(card)
            st.caption(f"Monthly Qualifying: ${preview:,.2f}")
            c1, c2 = st.columns(2)
            if c1.button("Remove", key=f"inc_remove_{idx}"):
                st.session_state.income_cards.pop(idx)
                st.experimental_rerun()
            if c2.button("Duplicate", key=f"inc_dup_{idx}"):
                st.session_state.income_cards.append(copy.deepcopy(card))
                st.experimental_rerun()
        total += _monthly_preview(card)
    st.markdown(f"**Total Monthly Income:** ${total:,.2f}")
    return total
