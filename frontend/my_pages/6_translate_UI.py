import streamlit as st
import logging
import asyncio
import httpx
import os
import json
from httpx import Cookies

PDF_PROCESSOR_URL = os.environ["PDF_PROCESSOR_URL"]
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if "processed_data" not in st.session_state or st.session_state.processed_data is None:
    st.session_state.processed_data = {}

if "httpx_cookies" not in st.session_state:
    st.session_state.httpx_cookies = Cookies()

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = None

if "translation_data" not in st.session_state:
    st.session_state.translation_data = {}

client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies)

st.header("📄 Translate Content")
translation_status = st.empty()
server_status = st.empty()
runner = asyncio.Runner()

async def submit_translation(doc_id: str, source_lang: str, target_lang: str) -> dict:
    """Submit a document for translation."""
    try:
        request_body = {
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        logger.info(f"Submitting translation: doc_id={doc_id}, source={source_lang}, target={target_lang}")
        logger.info(f"Request body: {request_body}")
        response = await client.post(
            f"{PDF_PROCESSOR_URL}/translation/{doc_id}",
            json=request_body
        )
        logger.info(f"Translation submission response: {response.status_code}")

        if response.status_code in [200, 201, 202]:
            return response.json()
        elif response.status_code == 409:
            # Document not ready for translation
            error_data = response.json()
            error_msg = error_data.get("detail", "Document is not ready for translation")
            logger.warning(f"Translation not ready: {error_msg}")
            return {"error": error_msg, "not_ready": True}
        else:
            logger.error(f"Translation submission failed: {response.text}")
            return {"error": f"HTTP {response.status_code}: {response.text}"}

    except Exception as e:
        logger.error(f"Error submitting translation: {e}")
        return {"error": str(e)}


async def get_translation_status(doc_id: str, max_retries=600, delay=1) -> dict:
    """Poll for translation completion."""
    for attempt in range(max_retries):
        try:
            response = await client.get(f"{PDF_PROCESSOR_URL}/translation/{doc_id}")
            logger.info(f"Translation status response: {response.status_code}")

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {response.text}: {e}")
                server_status.error("Received an invalid response from the server.")
                return {"error": "Invalid JSON response from server"}

            if response.status_code == 200 or response.status_code == 201:
                if data.get("status") == "completed":
                    server_status.success("Translation completed successfully")
                    logger.info(f"Translation completed: {data}")
                    return data
                elif data.get("status") == "failed":
                    server_status.error("Translation failed")
                    return {"error": "Translation failed"}
                else:
                    # Still processing
                    if attempt < max_retries - 1:
                        translation_status.info(f"Translating document... ({(attempt + 1) * delay}s)")
                        await asyncio.sleep(delay)
                        continue

            elif response.status_code == 202:
                if attempt < max_retries - 1:
                    translation_status.info(f"Translation processing... ({(attempt + 1) * delay}s)")
                    if "detail" in data:
                        server_status.info(data["detail"])
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise TimeoutError("Translation timed out after maximum retries")
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                response.raise_for_status()

        except httpx.RequestError as e:
            logger.error(f"Request error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(delay)

    raise TimeoutError("Max retries exceeded")


async def submit_rendering(doc_id: str) -> dict:
    """Submit a translated document for rendering."""
    try:
        response = await client.post(f"{PDF_PROCESSOR_URL}/renderer/{doc_id}")
        logger.info(f"Rendering submission response: {response.status_code}")

        if response.status_code in [200, 201, 202]:
            return response.json()
        else:
            logger.error(f"Rendering submission failed: {response.text}")
            return {"error": f"HTTP {response.status_code}: {response.text}"}

    except Exception as e:
        logger.error(f"Error submitting rendering: {e}")
        return {"error": str(e)}


async def get_rendering_status(doc_id: str, max_retries=600, delay=1) -> dict:
    """Poll for rendering completion."""
    for attempt in range(max_retries):
        try:
            response = await client.get(f"{PDF_PROCESSOR_URL}/renderer/{doc_id}")
            logger.info(f"Rendering status response: {response.status_code}")

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {response.text}: {e}")
                server_status.error("Received an invalid response from the server.")
                return {"error": "Invalid JSON response from server"}

            if response.status_code == 200 or response.status_code == 201:
                if data.get("status") == "completed":
                    server_status.success("Rendering completed successfully")
                    logger.info(f"Rendering completed: {data}")
                    return data
                elif data.get("status") == "failed":
                    server_status.error("Rendering failed")
                    return {"error": "Rendering failed"}
                else:
                    # Still processing
                    if attempt < max_retries - 1:
                        translation_status.info(f"Rendering document... ({(attempt + 1) * delay}s)")
                        await asyncio.sleep(delay)
                        continue

            elif response.status_code == 202:
                if attempt < max_retries - 1:
                    translation_status.info(f"Rendering processing... ({(attempt + 1) * delay}s)")
                    if "detail" in data:
                        server_status.info(data["detail"])
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise TimeoutError("Rendering timed out after maximum retries")
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                response.raise_for_status()

        except httpx.RequestError as e:
            logger.error(f"Request error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(delay)

    raise TimeoutError("Max retries exceeded")


async def get_rendered_pdf(doc_id: str) -> bytes:
    """Download the rendered PDF."""
    try:
        response = await client.get(f"{PDF_PROCESSOR_URL}/renderer/{doc_id}/rendered.pdf")
        logger.info(f"Rendered PDF download response: {response.status_code}")

        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Failed to download rendered PDF: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error downloading rendered PDF: {e}")
        return None


# Language options
LANGUAGES = {
    "auto": "Auto-detect",
    "en": "English",
    "zh": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "ru": "Russian",
    "pt": "Portuguese",
    "it": "Italian",
    "hi": "Hindi",
}


if "processed_data" in st.session_state and st.session_state.processed_data:
    # Initialize session state for expander states if not exists
    if "expander_states" not in st.session_state:
        st.session_state.expander_states = {}

    response_lst = list(st.session_state.processed_data.items())
    doc_names = [data["uploaded_filename"] for _, data in response_lst]

    # Initialize expander states for new documents
    for doc_name in doc_names:
        if doc_name not in st.session_state.expander_states:
            st.session_state.expander_states[doc_name] = True

    # Update multiselect based on expander states
    expanded_docs = st.multiselect(
        label="Expand documents:",
        options=doc_names,
        default=[
            doc for doc in doc_names if st.session_state.expander_states.get(doc, True)
        ],
        help="Choose which documents should be expanded",
        key="expander_multiselect",
    )

    # Update session state based on multiselect
    for doc_name in doc_names:
        st.session_state.expander_states[doc_name] = doc_name in expanded_docs

    try:
        for doc_id, data in response_lst:
            if data["uploaded_filename"] in doc_names:
                # Create expander
                file_lst = st.expander(
                    label=f"**{data['uploaded_filename']}**",
                    expanded=st.session_state.expander_states.get(
                        data["uploaded_filename"], True
                    ),
                )

                with file_lst:
                    st.markdown(f"**Document ID:** {doc_id}")
                    st.markdown(
                        f"**Filename:** [{data['filename']}]({data['download_url']})"
                    )

                    # Translation controls
                    col1, col2 = st.columns(2)

                    with col1:
                        source_lang = st.selectbox(
                            "Source Language",
                            options=list(LANGUAGES.keys()),
                            format_func=lambda x: LANGUAGES[x],
                            key=f"source_lang_{doc_id}",
                            index=0  # Default to auto-detect
                        )

                    with col2:
                        target_lang = st.selectbox(
                            "Target Language",
                            options=list(LANGUAGES.keys())[1:],  # Exclude auto-detect
                            format_func=lambda x: LANGUAGES[x],
                            key=f"target_lang_{doc_id}",
                            index=0  # Default to English
                        )

                    # Translate button
                    if st.button("Translate & Render", key=f"translate_btn_{doc_id}", type="primary"):
                        logger.info(f"Translation request: source={source_lang}, target={target_lang}")

                        with st.spinner("Processing translation and rendering..."):
                            # Step 1: Submit translation
                            translation_status.info("Submitting translation request...")
                            submit_result = runner.run(
                                submit_translation(doc_id, source_lang, target_lang)
                            )

                            if "error" in submit_result:
                                if submit_result.get("not_ready"):
                                    st.warning(submit_result['error'])
                                    st.info("Please wait for the document to finish processing (check Images tab), then try again.")
                                else:
                                    st.error(f"Translation submission failed: {submit_result['error']}")
                            else:
                                # Step 2: Poll for translation completion
                                translation_result = runner.run(
                                    get_translation_status(doc_id)
                                )

                                if "error" in translation_result:
                                    st.error(f"Translation failed: {translation_result['error']}")
                                else:
                                    st.success("Translation completed!")

                                    # Step 3: Submit for rendering
                                    translation_status.info("Submitting rendering request...")
                                    render_submit = runner.run(submit_rendering(doc_id))

                                    if "error" in render_submit:
                                        st.error(f"Rendering submission failed: {render_submit['error']}")
                                    else:
                                        # Step 4: Poll for rendering completion
                                        render_result = runner.run(
                                            get_rendering_status(doc_id)
                                        )

                                        if "error" in render_result:
                                            st.error(f"Rendering failed: {render_result['error']}")
                                        else:
                                            st.success("Rendering completed!")

                                            # Store result in session state
                                            st.session_state.translation_data[doc_id] = {
                                                "translation": translation_result,
                                                "rendering": render_result,
                                                "source_lang": source_lang,
                                                "target_lang": target_lang
                                            }

                                            # Clear status messages
                                            translation_status.empty()
                                            server_status.empty()

                                            st.rerun()

                    # Display rendered PDF if available
                    if doc_id in st.session_state.translation_data:
                        trans_data = st.session_state.translation_data[doc_id]

                        st.divider()
                        st.subheader("Translation Result")
                        st.markdown(f"**Source Language:** {LANGUAGES.get(trans_data['source_lang'], trans_data['source_lang'])}")
                        st.markdown(f"**Target Language:** {LANGUAGES.get(trans_data['target_lang'], trans_data['target_lang'])}")

                        # Download rendered PDF button
                        st.markdown("### Rendered PDF")

                        if st.button("Download Rendered PDF", key=f"download_btn_{doc_id}"):
                            with st.spinner("Downloading rendered PDF..."):
                                pdf_bytes = runner.run(get_rendered_pdf(doc_id))

                                if pdf_bytes:
                                    st.download_button(
                                        label="📥 Click to Save Rendered PDF",
                                        data=pdf_bytes,
                                        file_name=f"rendered_{data['uploaded_filename']}",
                                        mime="application/pdf",
                                        key=f"save_pdf_{doc_id}"
                                    )
                                else:
                                    st.error("Failed to download rendered PDF")

    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
        st.error("Processing timed out. Please try again.")
    except httpx.RequestError as e:
        logger.error(f"Network error: {e}")
        st.error(
            "There was a problem connecting to the server. Please check your connection and try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error in translation: {e}")
        st.error("An unexpected error occurred during translation.")

else:
    st.info("Please upload and process a PDF first to translate content")