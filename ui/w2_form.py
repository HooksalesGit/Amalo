import streamlit as st
from core.models import W2


def render_w2_form() -> None:
    """Render a minimal W-2 input form for testing purposes."""
    st.session_state.setdefault("w2_rows", [])
    if st.button("Add W2 Job", key="add_w2_job"):
        st.session_state.w2_rows.append(W2().model_dump())
    for idx, row in enumerate(st.session_state.w2_rows):
        with st.expander(f"W2 #{idx+1}"):
            items = list(row.items())
            for i in range(0, len(items), 2):
                cols = st.columns(2)
                for col_idx, (field, val) in enumerate(items[i : i + 2]):
                    with cols[col_idx]:
                        st.markdown(f"**{field}**")
                        st.caption(f"Enter {field}")
                        st.text_input("", value=str(val), key=f"w2_{idx}_{field}")
