import streamlit as st
import logging
from components.process_pdf import display_backend_status

logger = logging.getLogger(__name__)

st.header("📄 Settings")

display_backend_status()
