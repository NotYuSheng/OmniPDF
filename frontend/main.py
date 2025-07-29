from multiprocessing import process
from streamlit.components.v1 import html
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from io import BytesIO, StringIO
from PIL import Image
import pandas as pd
import requests
import base64
import json
import time
import os
import httpx
import asyncio

# Logger
import logging
logging.basicConfig(level=logging.INFO)
# Set up logger
logger = logging.getLogger(__name__)

# local imports
from components.process_pdf import display_backend_status

# Page configuration
st.set_page_config(
    page_title="OmniPDF",
    page_icon="🦸",
    layout="wide",
    initial_sidebar_state="expanded"
)
status_placeholder = st.empty()  # Placeholder for status updates
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None

# Backend
PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL", "http://pdf_processor_service:8000")
CHAT_URL = os.getenv("CHAT_URL", "http://chat_service:8000")

def process_pdf(uploaded_file):
    """
    Placeholder function for PDF processing
    In real implementation, this would call your backend API
    """
    # Simulate processing time
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(100):
        progress_bar.progress(i + 1)
        if i < 30:
            status_text.text('Extracting text and images...')
        elif i < 60:
            status_text.text('Translating content...')
        elif i < 80:
            status_text.text('Generating metadata...')
        else:
            status_text.text('Finalizing processing...')
        time.sleep(0.02)
    
    progress_bar.empty()
    status_text.empty()
    # Process pdf through PDF_processor endpoint
    try:
        # Step 1: Upload the PDF document
        logger.info(f"Uploading PDF: {uploaded_file}")

        # string($binary)
#         INFO:__main__:Uploading PDF: UploadedFile(file_id='824a1dc9-f613-4019-824f-093cfe9d73e1', name='testomni.pdf', type='application/pdf', size=150813, _file_urls=file_id: "824a1dc9-f613-4019-824f-093cfe9d73e1"
# upload_url: "/_stcore/upload_file/00487169-7f0f-4602-9d6d-f9e3c527d55f/824a1dc9-f613-4019-824f-093cfe9d73e1"
# delete_url: "/_stcore/upload_file/00487169-7f0f-4602-9d6d-f9e3c527d55f/824a1dc9-f613-4019-824f-093cfe9d73e1"
# )
        bytes_data = uploaded_file.getvalue() # bytes
        files = {'file': (uploaded_file.name, 
                                  bytes_data, 
                                  'application/pdf')}
        upload_response = requests.post(
            url=f"{PDF_PROCESSOR_URL}/documents/",
            files=files,
            )
        logger.info(f"Upload PDF response: {upload_response.text}")   
                
        upload_data = upload_response.json()
        doc_id = upload_data["doc_id"]
        filename = upload_data["filename"]
        download_url = upload_data["download_url"]
        st.session_state.processed_data = {
            "doc_id": doc_id,
            "filename": filename,
            "download_url": download_url
        }
        status_placeholder.write(f"Document uploaded successfully: {filename}")  
        logger.info(f"Processed data: {st.session_state.processed_data}")
        st.rerun()

        # Return processed data
        # return {
        #     "doc_id": "string",
        #     "status": "string",
        #     "result": {
        #         "schema_name": "string",
        #         "version": "string",
        #         "name": "string",
        #         "origin": "string",
        #         "furniture": "string",
        #         "texts": [
        #         "string"
        #         ],
        #         "pictures": [
        #         "string"
        #         ],
        #         "tables": [
        #         "string"
        #         ],
        #         "key_value_items": [
        #         "string"
        #         ],
        #         "form_items": [
        #         "string"
        #         ],
        #         "pages": "string"
        #     }
        # }
    except requests.exceptions.ConnectionError as e:
        st.error("Could not connect to PDF processor service. Please check if the service is running.")
        logger.error(f"Error processing PDF: {e}")
    
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        logger.error(f"Error processing PDF: {e}")

    
    # {
    #     "doc_id": "string",
    #     "status": "string",
    #     "result": {
    #         "schema_name": "string",
    #         "version": "string",
    #         "name": "string",
    #         "origin": "string",
    #         "furniture": "string",
    #         "texts": [
    #         "string"
    #         ],
    #         "pictures": [
    #         "string"
    #         ],
    #         "tables": [
    #         "string"
    #         ],
    #         "key_value_items": [
    #         "string"
    #         ],
    #         "form_items": [
    #         "string"
    #         ],
    #         "pages": "string"
    #     }
    # }
    # Step 2: Extract images
  
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

def translate_file(uploaded_file):
    pass

def generate_metadata(uploaded_file):
    pass

def upload_pdf_UI():
    st.header("📁 Upload PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a PDF file to process"
    )
    
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file
        
        # Processing options
        st.subheader("Processing Options")
        target_language = st.selectbox(
            "Target Language",
            ["English", "Spanish", "French", "German", "Chinese", "Japanese"]
        )
        
        extract_images = st.checkbox("Extract Images", value=True)
        generate_metadata = st.checkbox("Generate Metadata", value=True)
        enable_rag = st.checkbox("Enable RAG Chat", value=True)
        
        if st.button("🚀 Process PDF", type="primary"):
            with st.spinner("Processing PDF..."):
                # st.text(uploaded_file)
                st.session_state.processed_data = process_pdf(uploaded_file)
                st.success("Processing completed!")
                st.rerun()

def start_chat_UI():
    st.header("Chat")
    st.markdown("💬 Ask questions about the document content")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Chat interface
    chat_container = st.container(height=350)
    # with chat_container:
    #     # Display chat history
    #     for i, (question, answer) in enumerate(st.session_state.chat_history):
    #         st.markdown(f'<div class="chat-container">', unsafe_allow_html=True)
    #         st.markdown(f"You: {question}")
    #         st.markdown(f"Assistant: {answer}")
    #         st.markdown('</div>', unsafe_allow_html=True)

    # Chat interface
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Suggested questions
    st.text("💡 Suggested Questions")
    col1, col2 = st.columns(2)
    async def chat_with_rag(prompt):
        """
        Simulate a RAG response for the given prompt.
        Replace this with actual RAG implementation.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CHAT_URL}/documents/")
            if response.status_code == 200:
                return response.json()  # Job done, return result
            elif response.status_code == 202:
                await asyncio.sleep(1)
    

    def simulate_rag_response(prompt, document_content):
        # Placeholder response - replace with your actual RAG implementation
        return f"Response to: {prompt[:50]}..." if len(prompt) > 50 else f"Response to: {prompt}"
        
    with col1:
        if st.button("What is the main topic?"):
            response = simulate_rag_response("What is the main topic?", "document content")
            st.session_state.chat_history.append(("What is the main topic?", response))
        
        if st.button("Who are the authors?"):
            response = simulate_rag_response("Who are the authors?", "document content")
            st.session_state.chat_history.append(("Who are the authors?", response))
    
    with col2:
        if st.button("Summarize the document"):
            response = simulate_rag_response("Summarize the document", "document content")
            st.session_state.chat_history.append(("Summarize the document", response))
        
        if st.button("What are the key findings?"):
            response = simulate_rag_response("What are the key findings?", "document content")
            st.session_state.chat_history.append(("What are the key findings?", response))


    # Chat input
    if prompt := st.chat_input("Ask about the document"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
    
        # Generate and display assistant response
        response = simulate_rag_response(prompt, "document content")
        

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Rerun to update the interface
        st.rerun()

def translate_UI():
    st.write("📄 Translate Content")

def extract_images_UI():
    st.write("🖼️ Image Extraction")
       
    async def get_images(doc_id, max_retries=60, delay=1):
        for attempt in range(max_retries):
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(f"{PDF_PROCESSOR_URL}/images/{doc_id}")
                    logger.info(f"Image extraction response status: {response.status_code}")
                    logger.info(f"Image extraction response: {response.text}")
                   
                    if response.status_code == 200:
                        return response.json()  # Success - return the actual data
                    elif response.status_code == 202:
                        # Still processing, continue polling
                        if attempt < max_retries - 1:
                            st.info(f"Document still processing... (attempt {attempt + 1}/{max_retries})")
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
                image_data = asyncio.run(get_images(doc_id=doc_id))
            
            logger.info(f"Image data received: {image_data}")
            logger.info(f"[Cookie] Image data: {image_data.cookies}")

            
            # Check if we have images in the response
            if "images" in image_data and image_data["images"]:
                st.success(f"Found {len(image_data['images'])} images in the document")
                
                # if "cookies" not in st.session_state:
                #     st.session_state.cookies = image_data.get("cookies", {})

                # Display each image
                for i, (img_key, img_url) in enumerate(image_data["images"]):
                    with st.container():
                        st.markdown(f'<div class="image-container">', unsafe_allow_html=True)
                       
                        col1, col2 = st.columns([1, 2])
                        
                        with col1:
                            # Display actual image from URL
                            try:
                                st.image(
                                    img_url,
                                    caption=f"Image {i+1} (from {img_key})",
                                    use_column_width=True
                                )
                            except Exception as e:
                                logger.error(f"Error loading image {i+1}: {e}")
                                st.error(f"Error loading image {i+1}: {e}")
                       
                        with col2:
                            st.markdown(f"**Image Key:** {img_key}")
                            st.markdown(f"**Image ID:** IMG_{i+1:03d}")
                            st.markdown(f"**Image URL:** {img_url}")
                       
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
        
def extract_tables_UI():
    st.write("📋 Extract Tables")
    if 'tables' not in st.session_state:
        st.info("No tables found in the document.")
        return
    if "processed_data" in st.session_state and st.session_state.processed_data:
        data = st.session_state.processed_data
        tables = data.get('tables', [])
        if tables:
            for i, table_data in enumerate(tables):
                with st.container():
                    st.markdown(f'<div class="image-container">', unsafe_allow_html=True)
                    
                    st.markdown(f"**Table {i+1} (Page {table_data['page']})**")
                    
                    # Display table as CSV
                    try:
                        df = pd.read_csv(StringIO(table_data['csv']))
                        st.dataframe(df, use_container_width=True)
                        
                        # Download button for CSV
                        st.download_button(
                            label=f"📥 Download Table {i+1} (CSV)",
                            data=table_data['csv'],
                            file_name=f"table_{i+1}_page_{table_data['page']}.csv",
                            mime="text/csv"
                        )
                    except Exception as e:
                        st.error(f"Error displaying table: {e}")
                        st.text(table_data['csv'])
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No tables found in the document")
    else:
        st.info("Please upload and process a PDF first")

def metadata_UI():
    st.write("📊 PDF Metadata")
    if 'metadata' not in st.session_state:
        st.info("No metadata found in the document.")
        return
    if "processed_data" in st.session_state and st.session_state.processed_data:
        data = st.session_state.processed_data
        metadata = data['metadata']
        
        # Authors
        st.subheader("👥 Authors")
        for author in metadata['authors']:
            st.markdown(f"• {author}")
        
        # Executive Summary
        st.subheader("📋 Executive Summary")
        st.markdown(f'<div class="metric-card">{metadata["exec_summary"]}</div>', unsafe_allow_html=True)
        
        # Short Description
        st.subheader("📝 Short Description")
        st.markdown(f'<div class="metric-card">{metadata["short_description"]}</div>', unsafe_allow_html=True)
        
        # Keywords
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔤 Keywords")
            for keyword in metadata['keywords']:
                st.markdown(f"• {keyword}")
        
        with col2:
            st.subheader("🖼️ Image Keywords")
            for keyword in metadata['image_keywords']:
                st.markdown(f"• {keyword}")
        
        # Export metadata
        st.subheader("📤 Export Metadata")
        metadata_json = json.dumps(metadata, indent=2)
        st.download_button(
            label="📥 Download Metadata (JSON)",
            data=metadata_json,
            file_name="document_metadata.json",
            mime="application/json"
        )
    else:
        st.info("Please upload and process a PDF first")

def wordcloud_UI():
    st.write("☁️ Word Cloud")
    if 'metadata' not in st.session_state:
        st.info("No metadata found in the document.")
        return
    if "processed_data" in st.session_state and st.session_state.processed_data:
        # Generate word cloud from keywords
        all_keywords = st.session_state.processed_data['metadata']['keywords'] + st.session_state.processed_data['metadata']['image_keywords']
        
        if all_keywords:
            import io
            fig = generate_wordcloud(all_keywords)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches='tight')
            buf.seek(0)
            encoded = base64.b64encode(buf.read()).decode("utf-8")
            # Custom HTML for zoomable image
            html_code = f"""
            <style>
            .zoomable-img {{
                transition: transform 0.3s ease;
                cursor: zoom-in;
                max-width: 100%;
                height: auto;
            }}

            .zoomed {{
                transform: scale(2.5);
                cursor: zoom-out;
                z-index: 9999;
                position: relative;
            }}
            </style>

            <img id="zoom-img" class="zoomable-img" src="data:image/jpeg;base64,{encoded}" onclick="toggleZoom()" />

            <script>
            function toggleZoom() {{
                var img = document.getElementById("zoom-img");
                img.classList.toggle("zoomed");
            }}
            </script>
            """
            # Display the image using custom HTML
            html(html_code, height=600)
            st.pyplot(fig)
        else:
            st.info("No keywords available for word cloud generation")
    else:
        st.info("Please upload and process a PDF first to generate word cloud")


def main():
    # Custom CSS for better styling
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
        }
        
        .image-container {
            border: 2px solid #e6e6e6;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .chat-container {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-header">🦸 OmniPDF</h1>', unsafe_allow_html=True)

    # Full list of tab labels and corresponding keys
    tab_map = {
        "📂 Upload": "upload",
        "📄 Translate": "translate",
        "🖼️ Extract Images": "extract_images",
        "📋 Extract Tables": "extract_tables",
        "📊 Metadata": "metadata",
        "☁️ Word Cloud": "wordcloud",
        "💬 Chat": "chat",
        "⚙️": "settings"
    }

    # Initialize session state for sidebar-only tab selection
    if "sidebar_tab" not in st.session_state:
        st.session_state.sidebar_tab = "📂 Upload"  # default

    # Generate list of tabs excluding the selected sidebar-only one (except ⚙️ Settings)
    visible_tab_labels = [
        label for label in tab_map.keys()
        if label != st.session_state.sidebar_tab
    ]

    # Create Streamlit tabs
    tabs = st.tabs(visible_tab_labels)

    # Sidebar content (only show the selected one)
    with st.sidebar:
        selected_key = tab_map[st.session_state.sidebar_tab]
        st.markdown(f"### Sidebar: {st.session_state.sidebar_tab}")
        if selected_key == "chat":
            start_chat_UI()
        elif selected_key == "upload":
            upload_pdf_UI()
        status_placeholder = st.empty()
        status_placeholder.text("Waiting for document upload...")
        
        # Add other sidebar-only functions here

    # Render each tab
    for tab, label in zip(tabs, visible_tab_labels):
        key = tab_map[label]
        with tab:
            if key == "translate":
                translate_UI()
            elif key == "chat":
                start_chat_UI()
            elif key == "extract_images":
                extract_images_UI()
            elif key == "extract_tables":
                extract_tables_UI()
            elif key == "metadata":
                metadata_UI()
            elif key == "wordcloud":
                wordcloud_UI()
            elif key == "settings":
                st.markdown("### ⚙️ Settings")
                # Move the selectbox here
                selected = st.selectbox(
                    "Choose which tab should appear only in the sidebar:",
                    options=[label for label in tab_map.keys() if label != "⚙️"],
                    index=[label for label in tab_map].index(st.session_state.sidebar_tab),
                    key="sidebar_tab"  # binds directly to session_state
                )
                display_backend_status()

    
if __name__ == "__main__":
    main()
