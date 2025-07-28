from streamlit.components.v1 import html
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from io import BytesIO, StringIO
from PIL import Image
import pandas as pd
import requests
import base64
import json
import time
import os

# local imports
from components.process_pdf import is_pdf, display_backend_status

# Page configuration
st.set_page_config(
    page_title="OmniPDF",
    page_icon="🦸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend
BACKEND_URL = os.getenv("BACKEND_URL", "http://omnipdf-backend:8003")

def process_pdf(uploaded_file):
    """
    Placeholder function for PDF processing
    In real implementation, this would call your backend API
    """
    # Simulate processing time
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(100):
        progress_bar.progress(i + 1)
        if i < 30:
            status_text.text('Extracting text and images...')
        elif i < 60:
            status_text.text('Translating content...')
        elif i < 80:
            status_text.text('Generating metadata...')
        else:
            status_text.text('Finalizing processing...')
        time.sleep(0.02)
    
    progress_bar.empty()
    status_text.empty()
    # Process pdf through PDF_processor endpoint
    try:
        # Get the PDF processor URL from environment
        pdf_processor_url = os.getenv("PDF_PROCESSOR_URL", "http://localhost:8080/pdf_processor")
        
        # Step 1: Upload the PDF document
        files = {"file": ("document.pdf", uploaded_file.getvalue(), "application/pdf")}
        upload_response = requests.post(f"{pdf_processor_url}/documents/", files=files)
        
        if upload_response.status_code != 201:
            st.error(f"Failed to upload PDF: {upload_response.text}")
            return None
            
        upload_data = upload_response.json()
        doc_id = upload_data["doc_id"]
        
        # Step 2: Process images (if requested)
        images_data = []
        try:
            images_response = requests.get(f"{pdf_processor_url}/images/{doc_id}")
            if images_response.status_code == 200:
                images_data = images_response.json()["images"]
            elif images_response.status_code == 202:
                st.info("Images are still being processed. Please check back later.")
        except Exception as e:
            st.warning(f"Could not process images: {e}")
        
        # Step 3: Process tables (if requested)
        tables_data = []
        try:
            tables_response = requests.get(f"{pdf_processor_url}/tables/{doc_id}")
            if tables_response.status_code == 200:
                tables_data = tables_response.json()["tables"]
            elif tables_response.status_code == 202:
                st.info("Tables are still being processed. Please check back later.")
        except Exception as e:
            st.warning(f"Could not process tables: {e}")
        
        # Return processed data
        return {
            'doc_id': doc_id,
            'translated_pdf': upload_data["download_url"],
            'images': images_data,
            'tables': tables_data,
            'metadata': {
                'authors': ['Auto-detected'],
                'exec_summary': 'Document processed successfully through PDF processor service.',
                'short_description': 'PDF document with extracted content',
                'keywords': ['pdf', 'document', 'processed'],
                'image_keywords': ['extracted', 'images']
            }
        }
        
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to PDF processor service. Please check if the service is running.")
        return None
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None

def generate_wordcloud(text_data):
    """Generate word cloud from text data"""
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        colormap='viridis'
    ).generate(' '.join(text_data))
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    return fig

def translate_file(uploaded_file):
    pass

def generate_metadata(uploaded_file):
    pass

def check_backend():
    try:
        response = requests.get(f"{BACKEND_URL}/health")
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error checking backend: {e}")
        return False

def upload_pdf_UI():
    st.header("📁 Upload PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a PDF file to process"
    )
    
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file
        
        # Processing options
        st.subheader("Processing Options")
        target_language = st.selectbox(
            "Target Language",
            ["English", "Spanish", "French", "German", "Chinese", "Japanese"]
        )
        
        extract_images = st.checkbox("Extract Images", value=True)
        generate_metadata = st.checkbox("Generate Metadata", value=True)
        enable_rag = st.checkbox("Enable RAG Chat", value=True)
        
        if st.button("🚀 Process PDF", type="primary"):
            with st.spinner("Processing PDF..."):
                st.session_state.processed_data = process_pdf(uploaded_file)
            st.success("Processing completed!")
            st.rerun()

def start_chat_UI():
    st.header("Chat")
    st.markdown("💬 Ask questions about the document content")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat interface
    chat_container = st.container(height=350)
    if "chat_history" in st.session_state:
        with chat_container:
            # Display chat history
            for i, (question, answer) in enumerate(st.session_state.chat_history):
                st.markdown(f'<div class="chat-container">', unsafe_allow_html=True)
                st.markdown(f"You: {question}")
                st.markdown(f"Assistant: {answer}")
                st.markdown('</div>', unsafe_allow_html=True)
    
    # Display chat messages from history
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("What is up?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
    
        def simulate_rag_response(prompt, document_content):
            # Placeholder response - replace with your actual RAG implementation
            return f"Response to: {prompt[:50]}..." if len(prompt) > 50 else f"Response to: {prompt}"
        
        # Generate and display assistant response
        response = simulate_rag_response(prompt, "document content")
        
        def query_rag_response(prompt, document_content):
            try:
                response = requests.post(
                    url="http://localhost:8080/chat",
                    data="test"
                )
                return response
            except:
                return "The server is not responding" 

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Rerun to update the interface
        st.rerun()

def translate_UI():
    st.write("📄 Translate Content")

def extract_images_UI():
    st.write("🖼️ Image Extraction")
    if "processed_data" in st.session_state and st.session_state.processed_data:
        data = st.session_state.processed_data
        if data.get('images'):
            for i, img_data in enumerate(data['images']):
                with st.container():
                    st.markdown(f'<div class="image-container">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Display actual image from URL
                        try:
                            st.image(
                                img_data['url'],
                                caption=f"Image {i+1}",
                                use_column_width=True
                            )
                        except Exception as e:
                            # Fallback to placeholder if image loading fails
                            st.image(
                                "https://via.placeholder.com/300x200/4CAF50/FFFFFF?text=Image+{}".format(i+1),
                                caption=f"Image {i+1} (placeholder)",
                                use_column_width=True
                            )
                    
                    with col2:
                        st.markdown(f"**Image Key:** {img_data['image_key']}")
                        st.markdown(f"**Image ID:** IMG_{i+1:03d}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No images found in the document")
    else:
        st.info("Please upload and process a PDF first")

def extract_tables_UI():
    st.write("📋 Extract Tables")
    if "processed_data" in st.session_state and st.session_state.processed_data:
        data = st.session_state.processed_data
        if data.get('tables'):
            for i, table_data in enumerate(data['tables']):
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

def wordcloud_UI():
    st.write("☁️ Word Cloud")
    if "processed_data" in st.session_state and st.session_state.processed_data:
        # Generate word cloud from keywords
        all_keywords = st.session_state.processed_data['metadata']['keywords'] + st.session_state.processed_data['metadata']['image_keywords']
        
        if all_keywords:
            import io
            fig = generate_wordcloud(all_keywords)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches='tight')
            buf.seek(0)
            return base64.b64encode(buf.read()).decode("utf-8")
            # Custom HTML for zoomable image
            html_code = f"""
            <style>
            .zoomable-img {{
                transition: transform 0.3s ease;
                cursor: zoom-in;
                max-width: 100%;
                height: auto;
            }}

            .zoomed {{
                transform: scale(2.5);
                cursor: zoom-out;
                z-index: 9999;
                position: relative;
            }}
            </style>

            <img id="zoom-img" class="zoomable-img" src="data:image/jpeg;base64,{encoded}" onclick="toggleZoom()" />

            <script>
            function toggleZoom() {{
                var img = document.getElementById("zoom-img");
                img.classList.toggle("zoomed");
            }}
            </script>
            """

            # Display the image using custom HTML
            html(html_code, height=600)
            st.pyplot(fig)
        else:
            st.info("No keywords available for word cloud generation")
    else:
        st.info("Please upload and process a PDF first to generate word cloud")


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

    st.markdown('<h1 class="main-header">🦸 OmniPDF</h1>', unsafe_allow_html=True)

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
        if selected_key == "chat":
            start_chat_UI()
        elif selected_key == "upload":
            upload_pdf_UI()
        # Add other sidebar-only functions here

    # Render each tab
    for tab, label in zip(tabs, visible_tab_labels):
        key = tab_map[label]
        with tab:
            if key == "translate":
                translate_UI()
            elif key == "chat":
                start_chat_UI()
            elif key == "extract_images":
                extract_images_UI()
            elif key == "extract_tables":
                extract_tables_UI()
            elif key == "metadata":
                metadata_UI()
            elif key == "wordcloud":
                wordcloud_UI()
            elif key == "settings":
                st.markdown("### ⚙️ Settings")
                # Move the selectbox here
                selected = st.selectbox(
                    "Choose which tab should appear only in the sidebar:",
                    options=[label for label in tab_map.keys() if label != "⚙️"],
                    index=[label for label in tab_map].index(st.session_state.sidebar_tab),
                    key="sidebar_tab"  # binds directly to session_state
                )
                display_backend_status()

    
if __name__ == "__main__":
    main()
