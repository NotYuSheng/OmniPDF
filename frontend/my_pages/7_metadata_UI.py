import streamlit as st
import logging
import asyncio
import os
import json
import httpx
from components.documents import document_multiselect_with_expander, DocumentExpander

PDF_PROCESSOR_URL = os.environ["PDF_PROCESSOR_URL"]
logger = logging.getLogger(__name__)
client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies)

runner = asyncio.Runner()
# WIP - this file is not fully functional yet
st.header("☁️ Metadata")


async def get_metadata(doc_id: str, status_bar, max_retries=600, delay=1):
    for attempt in range(max_retries):
        try:
            response = await client.get(f"{PDF_PROCESSOR_URL}/metadata/{doc_id}")

            logger.info(f"metadata response status: {response.status_code}")
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                data = {}
                logger.error(
                    f"Failed to decode JSON from response: {response.text}: {e}"
                )

            if response.status_code == 200:
                status_bar.empty()
                return data  # Success - return the actual data
            elif response.status_code == 202:
                # Still processing, continue polling
                if attempt < max_retries - 1:
                    if status_bar:
                        reason = (
                            data.get("detail", "in progress") if data else "in progress"
                        )
                        status_bar.info(
                            f"Document still processing... ({(attempt + 1) * delay}s)"
                            f"\nReason: {reason}"
                        )
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise TimeoutError(
                        "Document processing timed out after maximum retries"
                    )
            response.raise_for_status()
        except httpx.RequestError as e:
            status_bar.error("Error Processing your file. Please try re uploading.")
            logger.error(f"Request error on attempt: {e}")
        except TimeoutError:
            logger.error(f"Document ID: {doc_id} took too long to process.")
            status_bar.error(
                "Retry limit reached. Please retry by clicking on page on left."
            )


async def display_metadata(expander: DocumentExpander):
    with expander:
        res = await get_metadata(expander.doc_id, expander.status)
        if res and res.get("metadata"):
            metadata = res["metadata"]

            # Display metadata fields in a structured way
            if metadata.get("title"):
                st.markdown(f"**Title:** {metadata['title']}")

            if metadata.get("authors"):
                authors = metadata["authors"]
                if isinstance(authors, list):
                    st.markdown(f"**Authors:** {', '.join(authors)}")
                else:
                    st.markdown(f"**Authors:** {authors}")

            if metadata.get("executive_summary"):
                st.markdown("**Executive Summary:**")
                st.info(metadata["executive_summary"])

            if metadata.get("summary"):
                st.markdown("**Full Summary:**")
                st.text_area("Summary", metadata["summary"], height=200, disabled=True, label_visibility="collapsed")

            if metadata.get("keywords"):
                keywords = metadata["keywords"]
                if isinstance(keywords, list):
                    st.markdown(f"**Keywords:** {', '.join(keywords)}")
                else:
                    st.markdown(f"**Keywords:** {keywords}")


async def display_all(expanders: list[DocumentExpander]):
    displays = [display_metadata(expander) for expander in expanders]
    await asyncio.gather(*displays, return_exceptions=True)


if "processed_data" in st.session_state and st.session_state.processed_data:
    # Initialize session state for expander states if not exists
    if "expander_states" not in st.session_state:
        st.session_state.expander_states = {}

    expanders = document_multiselect_with_expander()
    runner.run(display_all(expanders))

else:
    st.info("📤 No documents have been processed yet. Please upload and process a PDF first!")
    st.markdown("Go to the **Upload PDF** page to get started.")
