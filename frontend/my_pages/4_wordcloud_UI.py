import streamlit as st
import logging
import asyncio
import httpx
import os
import json
import html
from components.documents import document_multiselect_with_expander, DocumentExpander

PDF_PROCESSOR_URL = os.environ["PDF_PROCESSOR_URL"]
logger = logging.getLogger(__name__)
client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies)

runner = asyncio.Runner()
st.header("☁️ Word Cloud")


async def get_wordcloud(doc_id: str, status_bar, max_retries=600, delay=1):
    for attempt in range(max_retries):
        try:
            response = await client.get(f"{PDF_PROCESSOR_URL}/wordcloud/{doc_id}")

            logger.info(f"Wordcloud response status: {response.status_code}")
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


async def get_wordcloud_image(doc_id: str | None):
    if doc_id is None:
        return None
    try:
        response = await client.get(
            f"{PDF_PROCESSOR_URL}/wordcloud/{doc_id}/wordcloud.png"
        )

        logger.info(f"Wordcloud Image response status: {response.status_code}")
        response.raise_for_status()
        # return Image.open(BytesIO(response.content))
        return response.content
    except httpx.RequestError as e:
        logger.error(f"Request error on attempt: {e}")
        raise


async def display_wordcloud(expander: DocumentExpander):
    with expander:
        res = await get_wordcloud(expander.doc_id, expander.status)
        if res:
            img = await get_wordcloud_image(expander.doc_id)
            st.image(img)

            # Display top words as styled pills
            st.markdown("**Top Words:**")
            pills_html = '<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; margin-bottom: 20px;">'
            for word in res["top_words"]:
                escaped_word = html.escape(word)
                pills_html += f'<span style="background: rgba(128, 128, 128, 0.1); border: 1px solid rgba(128, 128, 128, 0.3); color: inherit; padding: 6px 14px; border-radius: 16px; font-size: 13px; font-weight: 400; display: inline-block;">{escaped_word}</span>'
            pills_html += '</div>'
            st.markdown(pills_html, unsafe_allow_html=True)


async def display_all(expanders: list[DocumentExpander]):
    displays = [display_wordcloud(expander) for expander in expanders]
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
