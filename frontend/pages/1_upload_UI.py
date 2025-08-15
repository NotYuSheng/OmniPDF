import asyncio
import logging
import os
import httpx

import streamlit as st

PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL", "http://localhost:8080/pdf_processor")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if 'processed_data' not in st.session_state or st.session_state.processed_data is None:
    st.session_state.processed_data = {}

# Ensure httpx_cookies is initialized
if 'httpx_cookies' not in st.session_state:
    st.session_state.httpx_cookies = None


async def process_pdf(uploaded_files, status_text):
    """
    Placeholder function for PDF processing
    In real implementation, this would call your backend API
    """
    # Simulate processing time
    progress_bar = st.progress(0)
    
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
        logger.info(f"Uploading PDF: {uploaded_files}")
        bytes_data = uploaded_files.getvalue() # bytes
        files = {'file': (uploaded_files.name, 
                                  bytes_data, 
                                  'application/pdf')}
        async with httpx.AsyncClient(cookies=st.session_state.httpx_cookies) as client:
            upload_response = await client.post(f"{PDF_PROCESSOR_URL}/documents/", files=files)
            if upload_response.cookies:
                st.session_state.httpx_cookies = upload_response.cookies
                
        logger.info(f"Upload PDF response: {upload_response.text}")   
                
        upload_data = upload_response.json()
        doc_id = upload_data["doc_id"]
        filename = upload_data["filename"]
        download_url = upload_data["download_url"]
        if 'processed_data' not in st.session_state or st.session_state.processed_data is None:
            st.session_state.processed_data = {}
        st.session_state.processed_data[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "download_url": download_url,
            "uploaded_filename": uploaded_files.name
        }
        status_text.success(f"Successfully processed! {uploaded_files.name}")
        
        # Display all processed files in this session

        # Check Set-Cookie header
        # set_cookie = upload_response.headers.get('Set-Cookie')
        # if set_cookie:
        #     logger.info(f"Set-Cookie: {set_cookie}")
        #     logger.info(f"Set-Cookie: {set_cookie}")
        #     st.session_state.set_cookie = set_cookie


    # except requests.exceptions.ConnectionError as e:
    #     st.error("Could not connect to PDF processor service. Please check if the service is running.")
    #     logger.error(f"Error processing PDF: {e}")

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        logger.error(f"Error processing PDF: {e}")

st.markdown('<h1 class="main-header">🦸 OmniPDF</h1>', unsafe_allow_html=True)
st.header("📁 Upload PDF")
uploaded_files = st.file_uploader(
    "Choose a PDF file",
    type=['pdf'],
    help="Upload a PDF file to process",
    accept_multiple_files=True
)

if uploaded_files:
    # Create a list of uploaded files for selection
    file_options = [file.name for file in uploaded_files]
    
    selection = st.multiselect(
        "Choose files to process:",
        options=file_options,
        default=file_options  # By default, select all uploaded files
    )

    # Check if files are selected and process button is clicked
    if st.button("Process PDF", type="primary"):
        status_text = st.empty()
        with st.spinner("Processing PDF..."):
            # Process each selected file
            for file_name in selection:
                # Find the corresponding file object
                file_to_process = next(file for file in uploaded_files if file.name == file_name)
                asyncio.run(process_pdf(file_to_process, status_text))

if uploaded_files is not None:
    st.session_state.uploaded_files = uploaded_files
    
# Initialize or update the status message
info_container = st.container()

with info_container:
    st.write(f"Total files processed in this session: {len(st.session_state.processed_data)}")
    