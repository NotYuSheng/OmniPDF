import streamlit as st
import logging
import asyncio
import httpx
import os
import base64
from httpx import Cookies

PDF_PROCESSOR_URL = os.environ["PDF_PROCESSOR_URL"]
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if "processed_data" not in st.session_state or st.session_state.processed_data is None:
    st.session_state.processed_data = {}

if "httpx_cookies" not in st.session_state:
    st.session_state.httpx_cookies = Cookies()

client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies, timeout=300.0)

st.header("🌐 Translation")


async def get_translation_status(doc_id: str) -> dict:
    """Get translation status for a document."""
    try:
        response = await client.get(f"{PDF_PROCESSOR_URL}/translation/{doc_id}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {"status": "not_found"}
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"Error getting translation status: {e}")
        return {"status": "error", "error": str(e)}


async def get_renderer_status(doc_id: str) -> dict:
    """Get renderer status for a document."""
    try:
        response = await client.get(f"{PDF_PROCESSOR_URL}/renderer/{doc_id}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {"status": "not_found"}
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"Error getting renderer status: {e}")
        return {"status": "error", "error": str(e)}


async def trigger_renderer(doc_id: str) -> dict:
    """Trigger rendering for a translated document."""
    try:
        response = await client.post(f"{PDF_PROCESSOR_URL}/renderer/{doc_id}")
        if response.status_code in [200, 201, 202]:
            return {"status": "success", "response_code": response.status_code}
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"Error triggering renderer: {e}")
        return {"status": "error", "error": str(e)}


def display_translation_info(translation_data: dict):
    """Display translation metadata and statistics."""
    result = translation_data.get("result", {})
    source_lang = translation_data.get("source_lang", "Unknown")
    target_lang = translation_data.get("target_lang", "Unknown")

    st.markdown(f"**Translation:** {source_lang} → {target_lang}")

    if result:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Text Elements", len(result.get("texts", [])))
        with col2:
            st.metric("Tables", len(result.get("tables", [])))
        with col3:
            st.metric("Images", len(result.get("pictures", [])))


def display_rendered_pdf(doc_id: str, filename: str, runner: asyncio.Runner):
    """Display rendered PDF with download and preview options."""
    # Server-side URL for fetching PDF (internal service communication)
    server_pdf_url = f"{PDF_PROCESSOR_URL}/renderer/{doc_id}/rendered.pdf"

    # Client-side URL for browser downloads (through nginx gateway)
    client_pdf_url = f"/pdf_processor/renderer/{doc_id}/rendered.pdf"

    try:
        pdf_response = runner.run(client.get(server_pdf_url))
        if pdf_response.status_code == 200:
            # Download button at the top
            st.download_button(
                label="📥 Download Translated PDF",
                data=pdf_response.content,
                file_name=f"{filename.rsplit('.', 1)[0]}_translated.pdf",
                mime="application/pdf",
                key=f"download_{doc_id}",
                use_container_width=True
            )

            # Preview section
            with st.expander("👁️ Preview PDF", expanded=False):
                base64_pdf = base64.b64encode(pdf_response.content).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
        else:
            st.error(f"Failed to load PDF (HTTP {pdf_response.status_code})")
            st.markdown(f"[Try direct download]({client_pdf_url})")
    except Exception as e:
        logger.error(f"Error fetching rendered PDF: {e}")
        st.error("Error loading PDF. Try the download link below:")
        st.markdown(f"[Download Translated PDF]({client_pdf_url})")


def display_renderer_section(doc_id: str, filename: str, renderer_data: dict, runner: asyncio.Runner):
    """Display renderer status and controls."""
    status = renderer_data.get("status")

    if status == "not_found":
        st.info("💡 Generate a translated PDF with the translated text overlaid on the original document.")
        if st.button("🎨 Generate Translated PDF", key=f"render_{doc_id}", use_container_width=True):
            with st.spinner("Generating translated PDF..."):
                trigger_result = runner.run(trigger_renderer(doc_id))
                if trigger_result.get("status") == "success":
                    st.success("✅ Generation started! Refreshing...")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {trigger_result.get('error', 'Unknown error')}")

    elif status == "processing":
        st.info("⏳ Generating translated PDF...")
        if st.button("🔄 Refresh", key=f"refresh_{doc_id}"):
            st.rerun()

    elif status == "completed":
        display_rendered_pdf(doc_id, filename, runner)

    elif status == "failed":
        st.error("❌ PDF generation failed")
        if st.button("🔄 Retry", key=f"retry_{doc_id}"):
            with st.spinner("Retrying..."):
                trigger_result = runner.run(trigger_renderer(doc_id))
                if trigger_result.get("status") == "success":
                    st.success("✅ Restarted! Refreshing...")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {trigger_result.get('error', 'Unknown error')}")

    elif status == "error":
        st.error(f"❌ {renderer_data.get('error', 'Unknown error')}")


# Main content
if "processed_data" in st.session_state and st.session_state.processed_data:
    response_lst = list(st.session_state.processed_data.items())

    if not response_lst:
        st.info("No documents have been processed yet. Upload a PDF to get started!")
    else:
        for doc_id, data in response_lst:
            with st.expander(f"📄 {data['uploaded_filename']}", expanded=True):
                runner = asyncio.Runner()
                translation_data = runner.run(get_translation_status(doc_id))

                status = translation_data.get("status")

                if status == "not_found":
                    st.warning("⚠️ No translation available for this document")
                    st.info("Translation was not enabled when this document was uploaded, or it's still processing.")

                elif status == "error":
                    st.error(f"❌ Error: {translation_data.get('error', 'Unknown error')}")

                elif status == "processing":
                    st.info("⏳ Translation is currently processing...")

                elif status == "completed":
                    st.success("✅ Translation completed!")
                    display_translation_info(translation_data)

                    # Check and display renderer section
                    renderer_data = runner.run(get_renderer_status(doc_id))
                    display_renderer_section(doc_id, data['uploaded_filename'], renderer_data, runner)

                elif status == "failed":
                    st.error("❌ Translation failed")
                    st.info("Please try uploading the document again.")

                else:
                    st.warning(f"Unknown status: {status}")

else:
    st.info("📤 No documents have been processed yet. Please upload and process a PDF first!")
    st.markdown("Go to the **Upload PDF** page to get started.")
