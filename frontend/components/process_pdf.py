from wordcloud import WordCloud
import matplotlib.pyplot as plt
import os
import streamlit as st
import logging
import httpx
import asyncio
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if the uploaded file is a valid PDF by checking the magic number
def is_pdf(file_obj):
    try:
        file_obj.seek(0)
        header = file_obj.read(5)
        file_obj.seek(0)
        return header == b"%PDF-"
    except Exception:
        return False


def generate_wordcloud(text_data):
    """Generate word cloud from text data"""
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        colormap='viridis'
    ).generate(' '.join(text_data))
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    return fig


def display_pdf(file):
    """Display PDF in an iframe on Streamlit."""
    with open(file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")

    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    return pdf_display


async def check_backend():
    """
    Check the health of specific backend services asynchronously.
    Returns a dictionary with service names and their health status.m
    """
    services = {
        "PDF Processor": os.getenv("PDF_PROCESSOR_URL", "http://pdf_processor_service:8000"),
        "PDF Extractor": os.getenv("PDF_EXTRACTOR_URL", "http://pdf_extraction_service:8000"),
        "Chat Service": os.getenv("CHAT_URL", "http://chat_service:8000"),
        "Translation Service": os.getenv("DOCLING_TRANSLATION_URL", "http://docling_translation_service:8000"),
        "Embedder Service": os.getenv("EMBEDDER_URL", "http://embedder_service:8000")
    }

    async def check_service(service_name, url):
        health_url = f"{url}/health"
        try:
            async with httpx.AsyncClient(cookies=st.session_state.httpx_cookies) as client:
                response = await client.get(health_url)

                if response.status_code == 200:
                    logger.info(f'{service_name}, "status": {response.text}, "url": {url}')
                    return service_name, {"status": "Healthy", "url": url}
                else:
                    logger.error(f'{service_name}, "status": {response.text}, "url": {url}')
                    logger.error(f"Health check: {response.text}")
                    return service_name, {"status": f"HTTP {response.status_code}", "url": url}
        except httpx.ConnectError:
            return service_name, {"status": "Connection Error", "url": url}
        except httpx.TimeoutException:
            return service_name, {"status": "Timeout", "url": url}
        except Exception as e:
            return service_name, {"status": f"Error: {str(e)}", "url": url}

    try:
        results = await asyncio.gather(*(check_service(name, url) for name, url in services.items()))
        return {name: status for name, status in results}
    except Exception as e:
        print(f"Error checking backend services: {e}")
        return {}



def display_backend_status():
    """
    Display the status of backend services in Streamlit.
    """
    st.subheader("🔧 Backend Services Status")
    
    backend_status = asyncio.run(check_backend())
    
    if not backend_status:
        st.error("Unable to check backend services")
        return
    
    # Create columns for better layout
    cols = st.columns(2)
    
    for i, (service_name, status_info) in enumerate(backend_status.items()):
        col = cols[i % 2]
        
        with col:
            if status_info["status"] == "Healthy":
                st.success(f"✅ {service_name}")
                st.caption(f"Status: {status_info['status']}")
            else:
                st.error(f"❌ {service_name}")
                st.caption(f"Status: {status_info['status']}")
                st.caption(f"URL: {status_info['url']}")

