from streamlit.components.v1 import html
import matplotlib.pyplot as plt
import streamlit as st
from io import BytesIO, StringIO
from PIL import Image
import pandas as pd
import requests
import json
import time
import os
import httpx
import asyncio

# Logger
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# local imports
from components.process_pdf import display_backend_status

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

# Backend
PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL", "http://pdf_processor_service:8000")
CHAT_URL = os.getenv("CHAT_URL", "http://chat_service:8000")

    

def extract_tables_UI():
    if 'tables' not in st.session_state:
        st.info("No tables found in the document.")
        return
    if "processed_data" in st.session_state and st.session_state.processed_data:
        data = st.session_state.processed_data
        tables = data.get('tables', [])
        if tables:
            for i, table_data in enumerate(tables):
                with st.container():
                    st.markdown(f'<div class="image-container">', unsafe_allow_html=True)
                    
                    st.markdown(f"**Table {i+1} (Page {table_data['page']})**")
                    
                    # Display table as CSV
                    try:
                        df = pd.read_csv(StringIO(table_data['csv']))
                        st.dataframe(df, use_container_width=True)
                        
                        # Download button for CSV
                        st.download_button(
                            label=f"📥 Download Table {i+1} (CSV)",
                            data=table_data['csv'],
                            file_name=f"table_{i+1}_page_{table_data['page']}.csv",
                            mime="text/csv"
                        )
                    except Exception as e:
                        st.error(f"Error displaying table: {e}")
                        st.text(table_data['csv'])
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No tables found in the document")
    else:
        st.info("Please upload and process a PDF first")

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

def main():
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

 
    # Full list of tab labels and corresponding keys
    tab_map = {
        "📂 Upload": "upload",
        "📄 Translate": "translate",
        "🖼️ Extract Images": "extract_images",
        "📋 Extract Tables": "extract_tables",
        "📊 Metadata": "metadata",
        "☁️ Word Cloud": "wordcloud",
        "💬 Chat": "chat",
        "⚙️": "settings"
    }

    # Initialize session state for sidebar-only tab selection
    if "sidebar_tab" not in st.session_state:
        st.session_state.sidebar_tab = "📂 Upload"  # default

    # Generate list of tabs excluding the selected sidebar-only one (except ⚙️ Settings)
    visible_tab_labels = [
        label for label in tab_map.keys()
        if label != st.session_state.sidebar_tab
    ]

    # Create Streamlit tabs
    tabs = st.tabs(visible_tab_labels)

    # Sidebar content (only show the selected one)
    with st.sidebar:
        selected_key = tab_map[st.session_state.sidebar_tab]
        st.markdown(f"### Sidebar: {st.session_state.sidebar_tab}")
        status_placeholder = st.empty()
        status_placeholder.text("Waiting for document upload...")
        
        # Add other sidebar-only functions here

    # Render each tab
    for tab, label in zip(tabs, visible_tab_labels):
        key = tab_map[label]
        with tab:
            if key == "extract_tables":
                extract_tables_UI()
            elif key == "metadata":
                metadata_UI()

    
if __name__ == "__main__":
    # main()
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

    st.sidebar = st