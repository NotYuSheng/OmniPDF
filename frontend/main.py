import streamlit as st
import logging
import os
import html

from httpx import Cookies
from version import __version__

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="OmniPDF",
    page_icon="🦸",
    layout="wide",
    initial_sidebar_state="expanded",
)
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None

if "httpx_cookies" not in st.session_state:
    st.session_state.httpx_cookies = Cookies()
# Backend
PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL")


if __name__ == "__main__":
    # Custom CSS for better styling
    st.markdown(
        """
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }

        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
        }

        .image-container {
            border: 2px solid #e6e6e6;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }

        /* Disable sidebar collapse button */
        [data-testid="collapsedControl"] {
            display: none;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    upload_UI = st.Page(
        page="my_pages/1_upload_UI.py",
        title="Upload PDF",
        icon="📂",
        default=True,  # to set this as the FIRST page upon establishing connection
    )

    images_UI = st.Page(
        page="my_pages/2_images_UI.py",
        title="Images",
        icon="🖼️"
    )

    tables_UI = st.Page(
        page="my_pages/3_tables_UI.py",
        title="Tables",
        icon="📋"
    )

    wordcloud_UI = st.Page(
        page="my_pages/4_wordcloud_UI.py",
        title="Word Cloud",
        icon="☁️"
    )

    translate_UI = st.Page(
        page="my_pages/6_translate_UI.py",
        title="Translated PDF",
        icon="📄",
    )

    metadata_UI = st.Page(
        page="my_pages/7_metadata_UI.py",
        title="Metadata",
        icon="📄",
    )

    settings_UI = st.Page(
        page="my_pages/10_settings_UI.py",
        title="Settings",
        icon="⚙️"
    )

    # To go between the different pages
    pg = st.navigation(
        pages=[
            upload_UI,
            images_UI,
            tables_UI,
            wordcloud_UI,
            translate_UI,
            metadata_UI,
            settings_UI,
        ]
    )

    # Add version number to sidebar footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"<div style='text-align: center; color: #666; font-size: 0.8em;'>v{html.escape(__version__)}</div>",
        unsafe_allow_html=True
    )

    pg.run()
