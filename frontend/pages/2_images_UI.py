import streamlit as st
import logging
import asyncio
import httpx
import json
import os
from PIL import Image
from io import BytesIO

PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL", "http://localhost:8080/pdf_processor")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FIXED_IMAGE_HEIGHT = 200  # Set your desired fixed height in pixels

st.header("🖼️ Image Extraction")
image_status = st.empty()
server_status = st.empty()

async def get_images(doc_id, max_retries=60, delay=1) -> dict:
    for attempt in range(max_retries):
        async with httpx.AsyncClient(cookies=st.session_state.httpx_cookies) as client:
            try:
                response = await client.get(f"{PDF_PROCESSOR_URL}/images/{doc_id}")
                
                logger.info(f"Image extraction response status: {response.status_code}")
                logger.info(f"Current session cookie: {st.session_state.httpx_cookies.get('OmniPDFSession')}")
                
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON from response: {response.text}: {e}")
                    server_status.error("Received an invalid response from the server.")
                
                # Use the decoded data for all subsequent checks
                if "detail" in data:
                    server_status.info(data["detail"])
                    logger.info(f"Info details: {data['detail']}")
                else:
                    server_status.info("Successfully retrieved images")
                    logger.info(f"Image extraction response: {response}")

                if response.status_code == 200:
                    return data  # Success - return the actual data
                elif response.status_code == 202:
                    # Still processing, continue polling
                    if attempt < max_retries - 1:
                        image_status.info(f"Document still processing... ({(attempt + 1)*delay}s)")
                        if "detail" in response.json():
                            server_status.info(response.json()["detail"])
                        else:
                            if len(data) > 100:
                                server_status.info(str(data)[:50] + "...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise TimeoutError("Document processing timed out after maximum retries")
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

    raise TimeoutError("Max retries exceeded")

def display_images(image_response, doc_id=None) -> None:
    """
    Display images extracted from the processed PDF document.
    """
     # Check if we have images in the response
    if "images" in image_response and image_response["images"]:
        image_status.success(f"Found {len(image_response['images'])} images in the document")
        
        # Display each image
        for i, image_data in enumerate(image_response["images"]):
            with st.container():
                col1, col2 = st.columns([1, 2], 
                                        border=True,
                                        vertical_alignment="top")
                
                image_path = f"/images/{doc_id}/{image_data['image_key'].split('/')[-1]}"
                image_url = f"{PDF_PROCESSOR_URL}{image_path}"
                logger.info(f"Fetching image from: {image_url}")
                        
                with col1:
                    # Display actual image from URL
                    try:
                        if "detail" in image_data:
                                st.error("An error occurred while loading the image.")
                        else:
                            # Fetch image with authenticated client
                            with httpx.Client(cookies=st.session_state.httpx_cookies) as client:
                                img_response = client.get(image_url)
                                img_response.raise_for_status()
                                image_bytes = img_response.content
                                
                                # Open image with PIL for potential resizing
                                img = Image.open(BytesIO(image_bytes))
                                width, height = img.size
                                
                                # Display the image
                                st.image(
                                    image_bytes,
                                    caption=f"Image {i+1} ({width}x{height}px)",
                                    use_container_width=True
                                )

                    except Exception as e:
                        logger.error(f"Error loading image {i+1}: {e}")
                        st.error(f"Error loading image {i+1}: {e}")
                
                with col2:
                    st.markdown(f"**Image Key:** {image_data["image_key"]}")
                    st.markdown(f"**Image ID:** IMG_{i+1:03d}")
                    st.markdown(f"**Image URL:** {image_data["url"]}")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
    else:
        logger.info("No images found in the document")
        st.info("No images found in the document")

def describe_image(image_data):
    """
    Placeholder function to describe the image.
    In a real application, this could call an AI model or service to generate a description.
    """
    # Simulate a description
    return "Description for image"


if "processed_data" in st.session_state and st.session_state.processed_data:
    # Initialize session state for expander states if not exists
    if 'expander_states' not in st.session_state:
        st.session_state.expander_states = {}
    
    response_lst = list(st.session_state.processed_data.items())
    doc_names = [data['uploaded_filename'] for _, data in response_lst]
    
    # Initialize expander states for new documents
    for doc_name in doc_names:
        if doc_name not in st.session_state.expander_states:
            st.session_state.expander_states[doc_name] = True
    
    # Update multiselect based on expander states
    expanded_docs = st.multiselect(
        label="Expand documents:",
        options=doc_names,
        default=[doc for doc in doc_names if st.session_state.expander_states.get(doc, True)],
        help="Choose which documents should be expanded",
        key="expander_multiselect"
    )
    
    # Update session state based on multiselect
    for doc_name in doc_names:
        st.session_state.expander_states[doc_name] = doc_name in expanded_docs

    try:
        image_responses = []
        # Show loading message
        with st.spinner("Extracting images from document..."):
            for doc_id, data in response_lst:
                if data['uploaded_filename'] in doc_names:
                    # Create expander and update state when it's clicked
                    expander_key = f"expander_{data['uploaded_filename']}"
                    file_lst = st.expander(
                        label=f"**{data['uploaded_filename']}**", 
                        expanded=st.session_state.expander_states.get(data['uploaded_filename'], True)
                    )
                    
                    # Update expander state and multiselect when expander is toggled
                    if not file_lst:  # expander is closed
                        st.session_state.expander_states[data['uploaded_filename']] = False
                        if data['uploaded_filename'] in expanded_docs:
                            expanded_docs.remove(data['uploaded_filename'])
                    else:  # expander is open
                        st.session_state.expander_states[data['uploaded_filename']] = True
                    
                    with file_lst:
                        st.markdown(f"**Document ID:** {doc_id}")
                        st.markdown(f"**Filename:** [{data['filename']}]({data['download_url']})") # Download link
                        logger.info(f"Extracting images for document ID: {doc_id}")
                        image_response = asyncio.run(get_images(doc_id=doc_id))
                        image_responses.append(image_response)
                        display_images(image_response, doc_id)

            
    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
        
    except httpx.RequestError as e:
        logger.error(f"Network error: {e}")
        st.info("There was a problem connecting to the server. Please check your connection and try again.")
        
    except Exception as e:
        logger.error(f"Unexpected error in image extraction: {e}")
        st.error("An unexpected error occurred at image extraction.")
        
else:
    st.info("Please upload and process a PDF first to extract images")