import streamlit as st
import logging
import asyncio
import httpx
import json
import os
from PIL import Image
from io import BytesIO
from components.documents import document_multiselect_with_expander, DocumentExpander


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


FIXED_IMAGE_HEIGHT = 200  # Set your desired fixed height in pixels

client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies)
a, b = st.columns([6, 1])
with a:
    st.header("🖼️ Image Extraction")

with b: 
    # Page-level refresh button
    if st.button("🔄 Refresh All", help="Refresh all"):
        st.rerun()

runner = asyncio.Runner()


async def get_images(doc_id, status_bar, max_retries=600, delay=1) -> dict | None:
    for attempt in range(max_retries):
        try:
            response = await client.get(f"{PDF_PROCESSOR_URL}/images/{doc_id}")

            logger.info(f"Image extraction response status: {response.status_code}")
            logger.info(
                f"Current session cookie: {st.session_state.httpx_cookies.get('OmniPDFSession')}"
            )

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to decode JSON from response: {response.text}: {e}"
                )
                return {"error": "Invalid JSON response from server"}
            
            if response.status_code == 200 or response.status_code == 201:
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
                    await asyncio.sleep(0)  # Yield to Streamlit
                    continue
                else:
                    raise TimeoutError(
                        "Document processing timed out after maximum retries"
                    )
            elif response.status_code == 450:
                # Processing failed
                error_msg = data.get("detail", "Processing failed") if data else "Processing failed"
                status_bar.error(f"Document processing failed: {error_msg}")
                logger.error(f"Document processing failed for {doc_id}: {error_msg}")
                return None
            response.raise_for_status()
        except httpx.RequestError as e:
            logger.error(f"Request error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                status_bar.warning(f"Connection error (attempt {attempt + 1}). Retrying...")
                await asyncio.sleep(delay)
                continue
            else:
                status_bar.error("Error Processing your file. Please try re uploading.")
                return None
        except TimeoutError:
            logger.error(f"Document ID: {doc_id} took too long to process.")
            status_bar.error(
                "Retry limit reached. Please retry by clicking on page on left."
            )
            return None

    raise TimeoutError("Max retries exceeded")


async def display_images(expander: DocumentExpander) -> None:
    """
    Display images extracted from the processed PDF document.
    """
    with expander:
        res = await get_images(expander.doc_id, expander.status)
        if res and res.get("images") and len(res["images"]) > 0:
            # st.dataframe(res["metadata"])
            st.success(f"Found {len(res['images'])} images in the document")
            # Display each image
            for i, image_data in enumerate(res["images"]):
                with st.container():
                    col1, col2 = st.columns([1, 2], border=True, vertical_alignment="top")

                    image_path = (
                        f"/images/{expander.doc_id}/{image_data['image_key'].split('/')[-1]}"
                    )
                    image_url = f"{PDF_PROCESSOR_URL}{image_path}"
                    logger.info(f"Fetching image from: {image_url}")
                    
                    image_bytes = None  # Initialize to handle scope issues
                            
                    with col1:
                        # Display actual image from URL
                        if "detail" in image_data:
                            st.error("An error occurred while loading the image.")
                        else:
                            # Fetch image with authenticated client
                            with httpx.Client(
                                cookies=st.session_state.httpx_cookies
                            ) as client:
                                img_response = client.get(image_url)
                                img_response.raise_for_status()
                                image_bytes = img_response.content

                                # Open image with PIL for potential resizing
                                img = Image.open(BytesIO(image_bytes))
                                width, height = img.size

                                # Display the image
                                st.image(
                                    image_bytes,
                                    caption=f"Image {i + 1} ({width}x{height}px)",
                                    use_container_width=True,
                                )


                    with col2:
                        st.markdown(f"**Image Key:** {image_data['image_key']}")
                        # Download button - only show if image was successfully loaded
                        if image_bytes:
                            filename = f"image_{i+1}.png"
                            st.download_button(
                                label="Download",
                                data=image_bytes,
                                file_name=filename,
                                mime="image/png",
                                key=f"{filename}_download_btn_{image_data['image_key']}"
                            )
                        else:
                            st.error("Image not available for download")
        else:
            # Handle cases where no images are found or processing failed
            if res and "detail" in res:
                st.warning("Failed to process document for image extraction")

async def display_all(expanders: list[DocumentExpander]):
    displays = [display_images(expander) for expander in expanders]
    await asyncio.gather(*displays, return_exceptions=True)
    with st.spinner("Embedding document for RAG..."):
        # Post - starts embedding, response from embed_pdf is 202
        embed_start = [embed_pdf(expander.doc_id, "semantic") for expander in expanders]
        await asyncio.gather(*embed_start, return_exceptions=True)

        # Get - checks if embedding is done
        embed_response = [display_embedding(expander) for expander in expanders] 
        await asyncio.gather(*embed_response, return_exceptions=True)



async def embed_pdf(doc_id: str, embed_type: str = "semantic", delay=1) -> dict | None:
    """
    Embedding PDF
    For rag
    """
    try:
        response = await client.post(f"{PDF_PROCESSOR_URL}/embed/{embed_type}/{doc_id}")
        logger.info(f"Embedding response: {response.text}")
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            data = {}
            logger.error(
                f"Failed to decode JSON from response: {response.text}: {e}"
            )
        notifications = st.empty()
        if response.status_code == 200:
            notifications.empty()
            return data  # Success - return the actual data
        else:
            reason = (
                data.get("detail", "in progress") if data else "in progress"
            )
            notifications.info(
                f"Document still processing...\n"
                f"\nReason: {reason}"
            )
            await asyncio.sleep(delay)

    except httpx.RequestError as e:
        logger.error(f"Request error during embedding: {e}")
        return None
    except Exception as e:
        logger.error(f"Error during embedding: {e}")
        return None
    
async def display_embedding(expander: DocumentExpander) -> None:
    with expander:

        res = await check_embedding_status(expander.doc_id, expander.status)
        logger.info(f"Embedding status for doc {expander.doc_id}: {res}")
        if res:
            st.subheader("Embedding Status")
            # Only show result column
            if isinstance(res, dict) and 'result' in res:
                # Convert to string to avoid Arrow serialization issues
                st.dataframe(res['result'])
            else:
                st.dataframe(res)

# Check if embedding is in progress
async def check_embedding_status(doc_id: str = None, status: str = None, max_retries: int = 100, delay: float = 1.0) -> bool:
    for attempt in range(max_retries):
        try:
            response = await client.get(f"{PDF_PROCESSOR_URL}/embed/semantic/{doc_id}")
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from embedding status response: {response.text}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    continue
                return False

            if response.status_code == 200:
                status.empty()
                return data
            elif response.status_code == 202:
                if status:
                    reason = data.get("detail", "in progress") if data else "in progress"
                    status.info(
                        f"Embedding still processing... ({(attempt + 1) * delay}s)"
                        f"\nReason: {reason}"
                    )
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f"Failed to get embedding status: {response.status_code}")
                if "detail" in data:
                    logger.error(f"Error details: {data['detail']}")
                    return data.get("detail", False)
                return False
        except httpx.RequestError as e:
            logger.error(f"Request error while checking embedding status (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                continue
            return False
    
    return False



def describe_image(image_data):
    """
    Placeholder function to describe the image.
    In a real application, this could call an AI model or service to generate a description.
    """
    # Simulate a description
    return "Description for image"


if "processed_data" in st.session_state and st.session_state.processed_data:
    # Initialize session state for expander states if not exists
    if "expander_states" not in st.session_state:
        st.session_state.expander_states = {}

    expanders = document_multiselect_with_expander()
    runner.run(display_all(expanders))
else:
    st.info("Please upload and process a PDF first to extract images")
