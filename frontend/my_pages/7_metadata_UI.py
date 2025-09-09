import asyncio
import os
import streamlit as st
import logging
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
        if res:
            st.dataframe(res["metadata"])


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
    st.info("Please upload and process a PDF first to extract images")
