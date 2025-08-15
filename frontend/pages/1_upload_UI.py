import asyncio
import logging
import os
import httpx

import streamlit as st

PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL", "http://pdf_processor_service:8000")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_pdf(uploaded_file):
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
        await asyncio.sleep(0.02)
    
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
        async with httpx.AsyncClient(cookies=st.session_state.httpx_cookies) as client:
            upload_response = await client.post(f"{PDF_PROCESSOR_URL}/documents/", files=files)
            st.session_state.httpx_cookies = upload_response.cookies
            logger.info(f"Upload response cookies: {upload_response.cookies['OmniPDFSession']}")
            
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
        status_text.success(f"PDF uploaded successfully! Document ID: {doc_id}")

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        logger.error(f"Error processing PDF: {e}")

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
            asyncio.run(process_pdf(uploaded_file))
            
    # Always show metadata if available
    if "processed_data" in st.session_state and st.session_state.processed_data:
        st.subheader("File Metadata")
        st.markdown(f"**Filename:** {uploaded_file.name}")
        size_unit = st.selectbox("File Size Unit", ["MB", "KB", "B"], index=0)
        if size_unit == "MB":
            size_val = uploaded_file.size / (1024 * 1024)
            size_str = f"{size_val:.2f} MB"
        elif size_unit == "KB":
            size_val = uploaded_file.size / 1024
            size_str = f"{size_val:.2f} KB"
        else:
            size_val = uploaded_file.size
            size_str = f"{size_val} B"
        st.markdown(f"**Size:** {size_str}")
        st.markdown(f"**Document ID:** {st.session_state.processed_data['doc_id']}")
        st.markdown(f"**Download URL:** {st.session_state.processed_data['download_url']}")