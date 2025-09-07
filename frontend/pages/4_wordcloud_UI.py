import asyncio
import os
import streamlit as st
import logging
import json 
import httpx


PDF_PROCESSOR_URL = os.environ["PDF_PROCESSOR_URL"]
logger = logging.getLogger(__name__)
client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies)

server_status = st.empty()
# WIP - this file is not fully functional yet
st.header("☁️ Word Cloud")


async def get_wordcloud(doc_id: str):
    try:
        response = await client.get(f"{PDF_PROCESSOR_URL}/wordcloud/{doc_id}")

        logger.info(f"Wordcloud response status: {response.status_code}")
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to decode JSON from response: {response.text}: {e}"
            )
            server_status.error("Received an invalid response from the server.")

        if response.status_code == 200:
            return data  # Success - return the actual data
        elif response.status_code == 202:
            server_status.error("Document is currently processing")
            return None
    except httpx.RequestError as e:
        logger.error(f"Request error on attempt: {e}")
        raise


async def get_wordcloud_image(doc_id: str | None):
    if doc_id is None:
        return None
    try:
        response = await client.get(f"{PDF_PROCESSOR_URL}/wordcloud/{doc_id}/wordcloud.png")

        logger.info(f"Wordcloud Image response status: {response.status_code}")
        response.raise_for_status()
        # return Image.open(BytesIO(response.content))
        return response.content
    except httpx.RequestError as e:
        logger.error(f"Request error on attempt: {e}")
        raise


async def get_wordclouds(doc_ids: list[str]):
    wordcloud_requests = [get_wordcloud(doc_id) for doc_id in doc_ids]
    return await asyncio.gather(*wordcloud_requests)


async def get_wordcloud_images(doc_ids: list[str]):
    image_requests = [get_wordcloud_image(doc_id) for doc_id in doc_ids]
    return await asyncio.gather(*image_requests)


if "processed_data" in st.session_state and st.session_state.processed_data:
    # Initialize session state for expander states if not exists
    if "expander_states" not in st.session_state:
        st.session_state.expander_states = {}

    doc_ids = st.session_state.processed_data.keys()
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

    with asyncio.Runner() as runner:
        wordcloud_response = runner.run(get_wordclouds(doc_ids))

        successful_doc_ids = [doc_id if response is not None else None for doc_id, response in zip(doc_ids, wordcloud_response)]
        images = runner.run(get_wordcloud_images(successful_doc_ids))

    for idx, doc_name in enumerate(doc_names):
        expander_key = f"expander_{doc_name}"
        wordcloud_tab = st.expander(
                        label=f"**{doc_name}**",
                        expanded=st.session_state.expander_states.get(
                            doc_name, True
                        ),
                    )
        
        # Update expander state and multiselect when expander is toggled
        if not wordcloud_tab:  # expander is closed
            st.session_state.expander_states[doc_name] = (
                False
            )
            if doc_name in expanded_docs:
                expanded_docs.remove(doc_name)
        else:  # expander is open
            st.session_state.expander_states[doc_name] = (
                True
            )
        with wordcloud_tab:
            if wordcloud_response is not None:
                st.image(images[idx])
                markdown_list = [f"- {word}" for word in wordcloud_response[idx]["top_words"]]
                st.markdown("\n".join(markdown_list))
            else:
                st.text("Processing.")

else:
    st.info("Please upload and process a PDF first to extract images")
