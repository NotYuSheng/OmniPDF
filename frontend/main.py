import streamlit as st
import logging
import json
import os

from httpx import Cookies

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="OmniPDF",
    page_icon="🦸",
    layout="wide",
    initial_sidebar_state="expanded"
)
status_placeholder = st.empty()  # Placeholder for status updates
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None

if "httpx_cookies" not in st.session_state:
    st.session_state.httpx_cookies = Cookies()
# Backend
PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL", "http://pdf_processor_service:8000")
CHAT_URL = os.getenv("CHAT_URL", "http://chat_service:8000")

    

def metadata_UI():
    st.write("📊 PDF Metadata")
    if 'metadata' not in st.session_state:
        st.info("No metadata found in the document.")
        return
    if "processed_data" in st.session_state and st.session_state.processed_data:
        data = st.session_state.processed_data
        metadata = data['metadata']
        
        # Authors
        st.subheader("👥 Authors")
        for author in metadata['authors']:
            st.markdown(f"• {author}")
        
        # Executive Summary
        st.subheader("📋 Executive Summary")
        st.markdown(f'<div class="metric-card">{metadata["exec_summary"]}</div>', unsafe_allow_html=True)
        
        # Short Description
        st.subheader("📝 Short Description")
        st.markdown(f'<div class="metric-card">{metadata["short_description"]}</div>', unsafe_allow_html=True)
        
        # Keywords
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔤 Keywords")
            for keyword in metadata['keywords']:
                st.markdown(f"• {keyword}")
        
        with col2:
            st.subheader("🖼️ Image Keywords")
            for keyword in metadata['image_keywords']:
                st.markdown(f"• {keyword}")
        
        # Export metadata
        st.subheader("📤 Export Metadata")
        metadata_json = json.dumps(metadata, indent=2)
        st.download_button(
            label="📥 Download Metadata (JSON)",
            data=metadata_json,
            file_name="document_metadata.json",
            mime="application/json"
        )
    else:
        st.info("Please upload and process a PDF first")

    
if __name__ == "__main__":
    # Custom CSS for better styling
    st.markdown("""
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
        
        .chat-container {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

    upload_UI = st.Page(
        page="pages/1_upload_UI.py",
        title="Upload PDF",
        icon="📂",
        default=True # to set this as the FIRST page upon establishing connection
    )


    images_UI = st.Page(
        page="pages/2_images_UI.py",
        title="Extract Images",
        icon="🖼️"
    )


    tables_UI = st.Page(
        page="pages/3_tables_UI.py",
        title="Extract Tables",
        icon="📋"
    )


    wordcloud_UI = st.Page(
        page="pages/4_wordcloud_UI.py",
        title="Word Cloud",
        icon="☁️"
    )

    chat_UI = st.Page(
        page="pages/5_chat_UI.py",
        title="Chat",
        icon="💬",
    )

    translate_UI = st.Page(
        page="pages/6_translate_UI.py",
        title="Translate",
        icon="📄",
    )

    settings_UI = st.Page(
        page="pages/10_settings_UI.py",
        title="Settings",
        icon="⚙️"
    )



    # To go between the different pages
    pg = st.navigation(pages=[upload_UI,
                              chat_UI, 
                              images_UI, 
                              tables_UI, 
                              wordcloud_UI,
                              translate_UI,
                              settings_UI])
    pg.run()
