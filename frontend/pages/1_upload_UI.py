import streamlit as st
import logging
import requests
import time
import os

PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL", "http://pdf_processor_service:8000")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        # Upload the PDF document
        logger.info(f"Uploading PDF: {uploaded_file}")
        bytes_data = uploaded_file.getvalue() # bytes
        files = {'file': (uploaded_file.name, 
                                  bytes_data, 
                                  'application/pdf')}
        upload_response = requests.post(
            url=f"{PDF_PROCESSOR_URL}/documents/",
            files=files,
            )
        logger.info(f"Upload PDF response: {upload_response.text}")   
                
        upload_data = upload_response.json()
        doc_id = upload_data["doc_id"]
        filename = upload_data["filename"]
        download_url = upload_data["download_url"]
        st.session_state.processed_data = {
            "doc_id": doc_id,
            "filename": filename,
            "download_url": download_url
        }

        # Check Set-Cookie header
        set_cookie = upload_response.headers.get('Set-Cookie')
        if set_cookie:
            print(f"Set-Cookie: {set_cookie}")
            logger.info(f"Set-Cookie: {set_cookie}")
            st.session_state.set_cookie = set_cookie

        return upload_response

    except requests.exceptions.ConnectionError as e:
        st.error("Could not connect to PDF processor service. Please check if the service is running.")
        logger.error(f"Error processing PDF: {e}")
        return None

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        logger.error(f"Error processing PDF: {e}")
        return None

st.markdown('<h1 class="main-header">🦸 OmniPDF</h1>', unsafe_allow_html=True)
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
    
    # Display Metadata here