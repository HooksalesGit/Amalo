import copy
import streamlit as st

DEBT_MODELS = {
    "installment": {
        "name": "",
        "monthly_payment": 0.0,
        "remaining_payments": 0,
        "payoff_at_close": False,
    },
    "revolving": {"name": "", "monthly_payment": 0.0, "payoff_at_close": False},
    "student_loan": {
        "name": "",
        "monthly_payment": 0.0,
        "balance": 0.0,
        "payoff_at_close": False,
    },
    "support": {"name": "", "monthly_payment": 0.0, "payoff_at_close": False},
}


def _default_payload(t: str) -> dict:
    return copy.deepcopy(DEBT_MODELS[t])


def render_debt_cards() -> float:
    st.session_state.setdefault("debt_cards", [])
    if st.button("Add Debt Card", key="add_debt_card"):
        st.session_state.debt_cards.append({"type": "installment", "payload": _default_payload("installment")})
    total = 0.0
    for idx, card in enumerate(list(st.session_state.debt_cards)):
        label = card["type"].replace("_", " ").title()
        with st.expander(f"Debt #{idx+1} — {label}"):
            sel = st.selectbox(
                "Type",
                list(DEBT_MODELS.keys()),
                index=list(DEBT_MODELS.keys()).index(card["type"]),
                key=f"debt_type_{idx}",
            )
            if sel != card["type"]:
                card["type"] = sel
                card["payload"] = _default_payload(sel)
            payload = card["payload"]
            items = list(payload.items())
            for i in range(0, len(items), 2):
                cols = st.columns(2)
                for col_idx, (f, v) in enumerate(items[i : i + 2]):
                    with cols[col_idx]:
                        label = f.replace("_", " ").title()
                        st.markdown(f"**{label}**")
                        st.caption(f"Enter {label}")
                        if isinstance(v, bool):
                            payload[f] = st.checkbox("", value=v, key=f"debt_{idx}_{f}")
                        elif isinstance(v, (int, float)):
                            payload[f] = st.number_input("", value=float(v), key=f"debt_{idx}_{f}")
                        else:
                            payload[f] = st.text_input("", value=v, key=f"debt_{idx}_{f}")
            preview = float(payload.get("monthly_payment", 0))
            st.caption(f"Monthly Payment: ${preview:,.2f}")
            c1, c2 = st.columns(2)
            if c1.button("Remove", key=f"debt_remove_{idx}"):
                st.session_state.debt_cards.pop(idx)
                st.experimental_rerun()
            if c2.button("Duplicate", key=f"debt_dup_{idx}"):
                st.session_state.debt_cards.append(copy.deepcopy(card))
                st.experimental_rerun()
        if not card["payload"].get("payoff_at_close", False):
            total += float(card["payload"].get("monthly_payment", 0))
    st.markdown(f"**Total Monthly Debts:** ${total:,.2f}")
    return total
