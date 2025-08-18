import streamlit as st
import logging
import asyncio
import httpx
import json
import os

PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL", "http://pdf_processor_service:8000")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


st.header("🖼️ Image Extraction")
image_status = st.empty()
server_status = st.empty()

async def get_images(doc_id, max_retries=60, delay=1):
    for attempt in range(max_retries):
        async with httpx.AsyncClient(cookies=st.session_state.httpx_cookies) as client:
            try:
                response = await client.get(f"{PDF_PROCESSOR_URL}/images/{doc_id}")
                logger.info(f"Image extraction response status: {response.status_code}")
                try:
                    data = response.json()
                    if "detail" in data:
                        server_status.info(data["detail"])
                        logger.info(f"Info details: {data['detail']}")
                    else:
                        server_status.info("Successfully retrieved images")
                        logger.info(f"Image extraction response: {response}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON from response: {response.text}")
                    server_status.error("Received an invalid response from the server.")
                
                if response.status_code == 200:
                    return response.json()  # Success - return the actual data
                elif response.status_code == 202:
                    # Still processing, continue polling
                    if attempt < max_retries - 1:
                        image_status.info(f"Document still processing... (attempt {attempt + 1}/{max_retries})")
                        if "detail" in response.json():
                            server_status.info(response.json()["detail"])
                        else:
                            if len(response.json()) > 100:
                                server_status.info(response.text[50:])
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
    
    raise TimeoutError("Max retries exceeded")

if "processed_data" in st.session_state and st.session_state.processed_data:
    doc_id = st.session_state.processed_data["doc_id"]
    
    try:
        # Show loading message
        with st.spinner("Extracting images from document..."):
            image_response = asyncio.run(get_images(doc_id=doc_id))
        
        
        # Check if we have images in the response
        if "images" in image_response and image_response["images"]:
            image_status.success(f"Found {len(image_response['images'])} images in the document")
            
            # if "cookies" not in st.session_state:
            #     st.session_state.cookies = image_response.get("cookies", {})

            # Display each image
            for i, image_data in enumerate(image_response["images"]):
                with st.container():
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Display actual image from URL
                        try:
                            st.image(
                                image_data["url"],
                                caption=f"Image {i+1} (from {image_data["image_key"]})",
                                use_container_width =True
                            )
                        except Exception as e:
                            logger.error(f"Error loading image {i+1}: {e}")
                            st.error(f"Error loading image {i+1}: {e}")
                    
                    with col2:
                        st.markdown(f"**Image Key:** {image_data["image_key"]}")
                        st.markdown(f"**Image ID:** IMG_{i+1:03d}")
                        st.markdown(f"**Image URL:** {image_data["url"]}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.divider()  # Add separator between images
        else:
            st.info("No images found in the document")
            
    except TimeoutError as e:
        st.error(f"Timeout error: {e}")
        st.info("The document is taking longer than expected to process. Please try again later.")
        
    except httpx.RequestError as e:
        st.error(f"Network error: {e}")
        st.info("There was a problem connecting to the server. Please check your connection and try again.")
        
    except Exception as e:
        logger.error(f"Unexpected error in image extraction: {e}")
        st.error(f"An unexpected error occurred: {e}")
        
else:
    st.info("Please upload and process a PDF first to extract images")