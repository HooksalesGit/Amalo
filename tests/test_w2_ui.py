from streamlit.testing.v1 import AppTest


def w2_form_app():
    import streamlit as st
    import app
    if "w2_rows" not in st.session_state:
        st.session_state["w2_rows"] = []
    app.render_w2_form()


def test_w2_ui_smoke():
    at = AppTest.from_function(w2_form_app)
    at.run()
    assert at.button("add_w2_job") is not None
