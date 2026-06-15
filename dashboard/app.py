"""
FIFA World Cup 2026 — Prediction & Analytics Platform
Streamlit entry point — redirects to Tournament Overview.
"""

import streamlit as st

st.set_page_config(
    page_title="WC 2026 Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.switch_page("pages/01_tournament_overview.py")
