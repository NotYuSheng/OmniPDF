import asyncio
import logging
import os
import random
import httpx

import streamlit as st

PDF_PROCESSOR_URL = os.environ["PDF_PROCESSOR_URL"]
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if "processed_data" not in st.session_state or st.session_state.processed_data is None:
    st.session_state.processed_data = {}

if "httpx_cookies" not in st.session_state:
    from httpx import Cookies

    st.session_state.httpx_cookies = Cookies()

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = None

client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies)


async def process_pdf(uploaded_file, status_text):
    """
    Placeholder function for PDF processing
    In real implementation, this would call your backend API
    """

    # Process pdf through PDF_processor endpoint
    try:
        # Upload the PDF document
        logger.info(f"Uploading PDF: {uploaded_file}")
        bytes_data = uploaded_file.getvalue()  # bytes
        files = {"file": (uploaded_file.name, bytes_data, "application/pdf")}

        upload_response = await client.post(
            f"{PDF_PROCESSOR_URL}/documents/", files=files
        )
        if upload_response.cookies:
            st.session_state.httpx_cookies = upload_response.cookies

        logger.info(f"Upload PDF response: {upload_response.text}")

        upload_data = upload_response.json()
        doc_id = upload_data.get("doc_id")
        filename = upload_data.get("filename")
        download_url = upload_data.get("download_url")

        st.session_state.processed_data[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "download_url": download_url,
            "uploaded_filename": uploaded_file.name,
        }
        status_text.success(f"Successfully processed! {uploaded_file.name}")

    except Exception as e:
        st.error("Error processing PDF")
        logger.error(f"Error processing PDF: {e}")


async def loader():
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(100):
        progress_bar.progress(i + 1)
        if i < 25:
            status_text.text("Extracting text and images...")
        elif i < 50:
            status_text.text("Translating content...")
        elif i < 75:
            status_text.text("Generating metadata...")
        else:
            status_text.text("Finalizing processing...")

        await asyncio.sleep(random.uniform(0.001, 0.03))

    progress_bar.empty()
    status_text.empty()


st.markdown('<h1 class="main-header">🦸 OmniPDF</h1>', unsafe_allow_html=True)
st.header("📁 Upload PDF")
uploaded_files = st.file_uploader(
    "Choose a PDF file",
    type=["pdf"],
    help="Upload a PDF file to process",
    accept_multiple_files=True,
)

if uploaded_files:
    # Create a list of uploaded files for selection
    file_options = [file.name for file in uploaded_files]

    selection = st.multiselect(
        "Choose files to process:",
        options=file_options,
        default=file_options,  # By default, select all uploaded files
    )

    # Check if files are selected and process button is clicked
    if st.button("Process PDF", type="primary"):
        status_text = st.empty()
        with st.spinner("Processing PDF..."):
            # Process each selected file
            async def _process_files():
                for file_name in selection:
                    # Find the corresponding file object
                    file_to_process = next(
                        file for file in uploaded_files if file.name == file_name
                    )
                    await process_pdf(file_to_process, status_text)

            asyncio.run(_process_files())
            # Simulate processing time
            asyncio.run(loader())

if uploaded_files is not None:
    st.session_state.uploaded_files = uploaded_files

# Initialize or update the status message
info_container = st.container()

with info_container:
    st.write(
        f"Total files processed in this session: {len(st.session_state.processed_data)}"
    )
