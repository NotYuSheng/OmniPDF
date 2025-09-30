import streamlit as st
import logging
from components.process_pdf import display_backend_status

logger = logging.getLogger(__name__)

st.header("📄 Settings")

# Initialize streaming preference
if "streaming_enabled" not in st.session_state:
    st.session_state.streaming_enabled = True


# Backend Status
st.subheader("🔗 Backend Status")
display_backend_status()
