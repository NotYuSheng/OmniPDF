import streamlit as st
import logging
import asyncio
import httpx
import os
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

client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies, timeout=300.0)  # 5 minute timeout for long translations

# Language options for translation
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


async def check_job_status(doc_id: str, endpoint: str):
    """Check the status of a specific job."""
    try:
        response = await client.get(f"{PDF_PROCESSOR_URL}/{endpoint}/{doc_id}")
        if response.status_code == 200:
            data = response.json()
            return data.get("status", "unknown")
        elif response.status_code == 404:
            return "not_started"
        elif response.status_code == 202:
            return "processing"
        else:
            return "unknown"
    except Exception as e:
        logger.error(f"Error checking {endpoint} status: {e}")
        return "error"


async def poll_processing_status(doc_id: str, status_container, progress_text, source_lang="", target_lang="", max_attempts=120, delay=2):
    """
    Poll the backend for processing status and update the UI.

    Processing stages:
    - Stage 1 (Sequential): Extraction
    - Stage 2 (Concurrent): Embedding + Translation (both depend only on extraction)
    - Stage 3 (Concurrent): Metadata (depends on embedding) + Renderer (depends on translation)
    """
    # Define processing stages with their dependencies
    stage_1 = {
        "extraction": {"name": "📄 PDF Extraction", "endpoint": "extractor", "status": "pending", "stage": 1}
    }

    stage_2 = {
        "embedding": {"name": "🔤 Text Embedding", "endpoint": "embed/sentence", "status": "pending", "stage": 2},
    }

    # Add translation to stage 2 if requested (concurrent with embedding)
    if source_lang and target_lang:
        stage_2["translation"] = {"name": "🌐 Translation", "endpoint": "translation", "status": "pending", "stage": 2}

    stage_3 = {
        "metadata": {"name": "📊 Metadata Generation", "endpoint": "metadata", "status": "pending", "stage": 3}
    }

    # Add renderer to stage 3 if translation is enabled (concurrent with metadata)
    if source_lang and target_lang:
        stage_3["renderer"] = {"name": "📑 PDF Rendering", "endpoint": "renderer", "status": "pending", "stage": 3}

    # Combine all stages
    stages = {**stage_1, **stage_2, **stage_3}

    # Track if translation and renderer have been triggered
    translation_triggered = False
    renderer_triggered = False

    for attempt in range(max_attempts):
        all_complete = True
        status_lines = []

        # STAGE 1: Check extraction status
        extraction_status = await check_job_status(doc_id, "extractor")
        stages["extraction"]["status"] = extraction_status

        # STAGE 2: After extraction completes, check embedding and translation concurrently
        if extraction_status == "completed":
            # Check embedding status
            embedding_status = await check_job_status(doc_id, "embed/sentence")
            stages["embedding"]["status"] = embedding_status

            # Check/trigger translation (concurrent with embedding)
            if "translation" in stages:
                if not translation_triggered:
                    translation_status = await check_job_status(doc_id, "translation")

                    # If translation not started, trigger it
                    if translation_status == "not_started":
                        try:
                            logger.info(f"Submitting translation for doc_id={doc_id}, source={source_lang}, target={target_lang}")

                            url = f"{PDF_PROCESSOR_URL}/translation/{doc_id}"
                            payload = {"source_lang": source_lang, "target_lang": target_lang}
                            logger.info(f"POST URL: {url}, payload: {payload}")

                            response = await client.post(url, json=payload)
                            logger.info(f"Translation POST response: {response.status_code}")

                            if response.status_code in [200, 201]:
                                translation_status = "completed"
                                logger.info(f"Translation completed successfully for {doc_id}")
                            elif response.status_code == 202:
                                translation_status = "processing"
                                logger.info(f"Translation processing for {doc_id}")
                            else:
                                logger.error(f"Translation returned unexpected status {response.status_code}")
                                translation_status = "failed"

                            translation_triggered = True
                        except Exception as e:
                            logger.error(f"Error submitting translation: {type(e).__name__}: {e}", exc_info=True)
                            translation_status = "failed"
                            translation_triggered = True

                    stages["translation"]["status"] = translation_status
                else:
                    # Already triggered, just check status
                    translation_status = await check_job_status(doc_id, "translation")
                    stages["translation"]["status"] = translation_status

            # STAGE 3: Concurrent processing after stage 2 completes
            # Metadata: Check after embedding completes (translation can still be running)
            if embedding_status == "completed":
                metadata_status = await check_job_status(doc_id, "metadata")
                stages["metadata"]["status"] = metadata_status

            # Renderer: Check/trigger after translation completes (embedding can still be running)
            if "renderer" in stages and "translation" in stages:
                translation_status = stages["translation"]["status"]
                if translation_status == "completed":
                    if not renderer_triggered:
                        renderer_status = await check_job_status(doc_id, "renderer")

                        # If renderer not started, trigger it
                        if renderer_status == "not_started":
                            try:
                                logger.info(f"Submitting renderer for doc_id={doc_id}")

                                url = f"{PDF_PROCESSOR_URL}/renderer/{doc_id}"
                                logger.info(f"POST URL: {url}")

                                response = await client.post(url)
                                logger.info(f"Renderer POST response: {response.status_code}")

                                if response.status_code in [200, 201]:
                                    renderer_status = "completed"
                                    logger.info(f"Renderer completed successfully for {doc_id}")
                                elif response.status_code == 202:
                                    renderer_status = "processing"
                                    logger.info(f"Renderer processing for {doc_id}")
                                else:
                                    logger.error(f"Renderer returned unexpected status {response.status_code}")
                                    renderer_status = "failed"

                                renderer_triggered = True
                            except Exception as e:
                                logger.error(f"Error submitting renderer: {type(e).__name__}: {e}", exc_info=True)
                                renderer_status = "failed"
                                renderer_triggered = True

                        stages["renderer"]["status"] = renderer_status
                    else:
                        # Already triggered, just check status
                        renderer_status = await check_job_status(doc_id, "renderer")
                        stages["renderer"]["status"] = renderer_status

        # Build status display grouped by stage
        stage_1_lines = []
        stage_2_lines = []
        stage_3_lines = []
        current_stages = []

        for stage_key, stage_info in stages.items():
            status = stage_info["status"]
            name = stage_info["name"]
            stage_num = stage_info["stage"]

            # Format status line
            if status == "completed":
                line = f"✅ {name}"
            elif status == "processing":
                line = f"⏳ {name}"
                current_stages.append(name)
                all_complete = False
            elif status == "failed":
                line = f"❌ {name}"
                all_complete = False
            elif status == "not_started" or status == "pending":
                line = f"⏸️ {name}"
                all_complete = False
            else:
                line = f"❓ {name}"
                all_complete = False

            # Group by stage
            if stage_num == 1:
                stage_1_lines.append(line)
            elif stage_num == 2:
                stage_2_lines.append(line)
            elif stage_num == 3:
                stage_3_lines.append(line)

        # Build final status display with stage grouping
        status_lines = ["**Stage 1 - Extraction:**"] + stage_1_lines
        if stage_2_lines:
            status_lines.append("\n**Stage 2 - Concurrent Processing:**")
            status_lines.extend(stage_2_lines)
        if stage_3_lines:
            status_lines.append("\n**Stage 3 - Final Processing:**")
            status_lines.extend(stage_3_lines)

        # Update the status display
        status_container.markdown("**Processing Status:**\n\n" + "\n\n".join(status_lines))

        # Update progress text for spinner
        if current_stages:
            if len(current_stages) > 1:
                progress_text.text(f"Processing: {', '.join(current_stages)}...")
            else:
                progress_text.text(f"Processing: {current_stages[0]}...")

        # Check if all stages are complete
        if all_complete:
            status_container.success("✅ All processing stages complete!")
            progress_text.empty()
            return True

        # Check for any failures
        if any(s["status"] == "failed" for s in stages.values()):
            status_container.error("❌ Processing failed. Check the logs for details.")
            progress_text.empty()
            return False

        await asyncio.sleep(delay)

    status_container.warning("⚠️ Processing timeout. Some stages may still be running.")
    progress_text.empty()
    return False


async def process_pdf(uploaded_file, file_expander, source_lang="", target_lang=""):
    """
    Uploads PDF to backend and stores document metadata in session state.
    Optionally triggers translation if languages are specified.
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
            st.session_state.httpx_cookies.update(upload_response.cookies)

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

        with file_expander:
            st.success(f"✅ Uploaded: {uploaded_file.name}")

            # Show translation info if configured
            if source_lang and target_lang:
                st.info(f"🌐 Translation: {LANGUAGES.get(source_lang, source_lang)} → {LANGUAGES.get(target_lang, target_lang)}")

            # Create status containers
            status_container = st.empty()
            progress_text = st.empty()

            # Poll for processing status with spinner
            with st.spinner("Processing document..."):
                await poll_processing_status(doc_id, status_container, progress_text, source_lang, target_lang)

    except Exception as e:
        with file_expander:
            st.error(f"❌ Error processing PDF: {uploaded_file.name}")
        logger.error(f"Error processing PDF: {e}")




st.markdown('<h1 class="main-header">🦸 OmniPDF</h1>', unsafe_allow_html=True)
st.header("📁 Upload PDF")
uploaded_files = st.file_uploader(
    "Choose a PDF file",
    type=["pdf"],
    help="Upload a PDF file to process",
    accept_multiple_files=True,
)

if uploaded_files:
    # Initialize translation settings in session state if not exists
    if "translation_settings" not in st.session_state:
        st.session_state.translation_settings = {}

    # Prune stale translation settings for removed files
    current_file_names = {f.name for f in uploaded_files}
    stale_files = set(st.session_state.translation_settings.keys()) - current_file_names
    for file_name in stale_files:
        del st.session_state.translation_settings[file_name]

    # Create a list of uploaded files for selection
    file_options = [file.name for file in uploaded_files]

    selection = st.multiselect(
        "Choose files to process:",
        options=file_options,
        default=file_options,  # By default, select all uploaded files
    )

    # Translation configuration per file
    st.markdown("---")
    st.subheader("🌐 Translation Settings")
    st.markdown("Configure translation settings for each file individually:")

    # Create translation settings for each selected file
    for file_name in selection:
        with st.expander(f"📄 {file_name}", expanded=True):
            col1, col2 = st.columns(2)

            # Initialize default values if not already set
            if file_name not in st.session_state.translation_settings:
                st.session_state.translation_settings[file_name] = {
                    "source_lang": "auto",
                    "target_lang": "en"
                }

            with col1:
                source_lang = st.selectbox(
                    "Source Language",
                    options=list(LANGUAGES.keys()),
                    format_func=lambda x: LANGUAGES[x],
                    key=f"source_lang_{file_name}",
                    index=list(LANGUAGES.keys()).index(st.session_state.translation_settings[file_name]["source_lang"]),
                    help="Select source language for automatic detection or specify a language"
                )
                st.session_state.translation_settings[file_name]["source_lang"] = source_lang

            with col2:
                target_lang = st.selectbox(
                    "Target Language",
                    options=list(LANGUAGES.keys()),
                    format_func=lambda x: LANGUAGES[x],
                    key=f"target_lang_{file_name}",
                    index=list(LANGUAGES.keys()).index(st.session_state.translation_settings[file_name]["target_lang"]),
                    help="Select target language for translation"
                )
                st.session_state.translation_settings[file_name]["target_lang"] = target_lang

            st.info(f"🌐 Translation: {LANGUAGES[source_lang]} → {LANGUAGES[target_lang]}")

    st.markdown("---")

    # Check if files are selected and process button is clicked
    if st.button("Process PDF", type="primary"):
        # Create a container for all processing status
        st.markdown("---")
        st.subheader("📊 Processing Status")

        # Status legend
        legend_parts = ["✅ Complete", "⏳ Processing", "⏸️ Waiting", "❌ Failed"]
        st.markdown(f"**Status Legend:** {' | '.join(legend_parts)}")
        st.markdown("---")

        # Process each selected file
        async def _process_files():
            for file_name in selection:
                # Find the corresponding file object
                file_to_process = next(
                    file for file in uploaded_files if file.name == file_name
                )

                # Get translation settings for this specific file
                file_translation = st.session_state.translation_settings.get(file_name, {})
                file_source_lang = file_translation.get("source_lang", "auto")
                file_target_lang = file_translation.get("target_lang", "en")

                # Create an expander for each file
                file_expander = st.expander(f"📄 {file_name}", expanded=True)

                # Pass file-specific translation settings
                await process_pdf(file_to_process, file_expander, file_source_lang, file_target_lang)

        asyncio.run(_process_files())

        st.success("🎉 All files processed!")

if uploaded_files is not None:
    st.session_state.uploaded_files = uploaded_files

# Initialize or update the status message
info_container = st.container()

with info_container:
    st.write(
        f"Total files processed in this session: {len(st.session_state.processed_data)}"
    )
