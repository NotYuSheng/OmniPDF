import streamlit as st
import logging
from components.process_pdf import display_backend_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.write("📄 Settings")

display_backend_status()
