import streamlit as st
import logging
import asyncio
import httpx
import os
import json
from PIL import Image
from io import BytesIO

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

st.header("🖼️ Image Extraction")
image_status = st.empty()
server_status = st.empty()
runner = asyncio.Runner()


async def get_images(doc_id, max_retries=600, delay=1) -> dict:
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
                server_status.error("Received an invalid response from the server.")
                return {"error": "Invalid JSON response from server"}
            
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"Image extraction response: {response}")
                return data  # Success - return the actual data
            elif response.status_code == 202:
                if "detail" in data:
                    server_status.info(data["detail"])
                    logger.info(f"Info details: {data['detail']}")
                
                # Still processing, continue polling
                if attempt < max_retries - 1:
                    image_status.info(
                        f"Document still processing... ({(attempt + 1) * delay}s)"
                    )
                    data = response.json()
                    if "detail" in data:
                        server_status.info(data["detail"])
                    else:
                        if len(data) > 100:
                            server_status.info(str(data)[:50] + "...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise TimeoutError(
                        "Document processing timed out after maximum retries"
                    )
            else:
                # Handle other HTTP errors
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


def display_images(image_response, doc_id=None) -> None:
    """
    Display images extracted from the processed PDF document.
    """
    # Check if we have a valid response first
    if not image_response or "error" in image_response:
        st.error(f"Error in image response: {image_response.get('error', 'Unknown error')}")
        return
        
    # Check if we have images in the response
    if "images" in image_response and image_response["images"]:
        # Display each image
        for i, image_data in enumerate(image_response["images"]):
            with st.container():
                col1, col2 = st.columns([1, 2], border=True, vertical_alignment="top")

                image_path = (
                    f"/images/{doc_id}/{image_data['image_key'].split('/')[-1]}"
                )
                image_url = f"{PDF_PROCESSOR_URL}{image_path}"
                logger.info(f"Fetching image from: {image_url}")
                
                image_bytes = None  # Initialize to handle scope issues
                        
                with col1:
                    # Display actual image from URL
                    try:
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

                    except Exception as e:
                        logger.error(f"Error loading image {i + 1}: {e}")
                        st.error(f"Error loading image {i + 1}: {e}")

                with col2:
                    # Display AI-generated caption if available
                    if 'caption' in image_data and image_data['caption']:
                        st.markdown(f"**Caption:** {image_data['caption']}")

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
        logger.info("No images found in the document")
        st.info("No images found in the document")

async def embed_pdf(embed_type: str, doc_id: str) -> dict | None:
    """
    Embedding PDF
    For rag
    """
    try:
        response = await client.post(f"{PDF_PROCESSOR_URL}/embed/{embed_type}/{doc_id}")
        logger.info(f"Embedding response: {response.text}")
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"Request error during embedding: {e}")
        return None
    except Exception as e:
        logger.error(f"Error during embedding: {e}")
        return None
    

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

    response_lst = list(st.session_state.processed_data.items())
    doc_names = [data["uploaded_filename"] for _, data in response_lst]

    # Initialize expander states for new documents
    for doc_name in doc_names:
        if doc_name not in st.session_state.expander_states:
            st.session_state.expander_states[doc_name] = True


    try:
        # Show loading message
        with st.spinner("Extracting images from document..."):
            for doc_id, data in response_lst:
                if data["uploaded_filename"] in doc_names:
                    # Create expander and update state when it's clicked
                    expander_key = f"expander_{data['uploaded_filename']}"
                    file_lst = st.expander(
                        label=f"**{data['uploaded_filename']}**",
                        expanded=st.session_state.expander_states.get(
                            data["uploaded_filename"], True
                        ),
                    )

                    # Update expander state when expander is toggled
                    if not file_lst:  # expander is closed
                        st.session_state.expander_states[data["uploaded_filename"]] = False
                    else:  # expander is open
                        st.session_state.expander_states[data["uploaded_filename"]] = True

                    with file_lst:
                        logger.info(f"Extracting images for document ID: {doc_id}")

                        image_response = runner.run(get_images(doc_id=doc_id))
                        logger.info(f"Image response: {image_response}")
                        display_images(image_response, doc_id)

                        embed_response = runner.run(embed_pdf(embed_type="sentence", doc_id=doc_id))
                        logger.info(f"Embedding response: {embed_response}")
                        if embed_response and "error" not in embed_response:
                            pass  # Successfully embedded
                        else:
                            st.toast("Error during embedding",
                                     icon="❌")


    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
    except httpx.RequestError as e:
        logger.error(f"Network error: {e}")
        st.info(
            "There was a problem connecting to the server. Please check your connection and try again."
        )

    except Exception as e:
        logger.error(f"Unexpected error in image extraction: {e}")
        st.error("An unexpected error occurred at image extraction.")

else:
    st.info("📤 No documents have been processed yet. Please upload and process a PDF first!")
    st.markdown("Go to the **Upload PDF** page to get started.")
