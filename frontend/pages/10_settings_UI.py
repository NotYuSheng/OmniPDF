import streamlit as st
import logging
from components.process_pdf import display_backend_status

logger = logging.getLogger(__name__)

st.header("📄 Settings")

# Initialize streaming preference
if "streaming_enabled" not in st.session_state:
    st.session_state.streaming_enabled = True

# Chat Settings
st.subheader("💬 Chat Settings")
st.session_state.streaming_enabled = st.toggle(
    "Stream chat responses", 
    value=st.session_state.streaming_enabled,
    help="Enable word-by-word streaming effect for AI responses"
)

st.divider()

# Backend Status
st.subheader("🔗 Backend Status")
display_backend_status()
