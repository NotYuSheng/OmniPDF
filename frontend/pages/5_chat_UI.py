import streamlit as st
import logging
import asyncio
import httpx
import json
import os

CHAT_URL = os.getenv("CHAT_URL")
PDF_PROCESSOR_URL = os.getenv("PDF_PROCESSOR_URL")
logger = logging.getLogger(__name__)

st.header("Chat")
st.markdown("💬 Ask questions about the document content")
runner = asyncio.Runner()

# Status containers for user feedback
chat_status = st.empty()
server_status = st.empty()

# Initialize cookies if not present
if 'httpx_cookies' not in st.session_state:
    st.session_state.httpx_cookies = httpx.Cookies()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat interface
chat_container = st.container(height=350)

# Chat interface
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(name=message["role"]):
            st.write(message["content"])
    
client = httpx.AsyncClient(cookies=st.session_state.httpx_cookies)

async def chat_with_rag(prompt: str, doc_ids: list[str] = None, collection_name: str = "SemanticEmbeds", max_retries: int = 600, delay: int = 1):
    """
    Send chat request to RAG backend and handle the response.
    """
    logger.info(f"Sending chat request with doc_ids: {doc_ids}")
    for attempt in range(max_retries):
        try:
            response = await client.post(url=f"{PDF_PROCESSOR_URL}/chat/",
                                        json={"message": prompt,
                                            "doc_ids": doc_ids,
                                            "collection_name": "SemanticEmbeds"
                                        })
            
            logger.info(f"Chat response status: {response.status_code}")
            logger.info(f"Chat response text: {response.text}")
            logger.info(f"Current session cookie: {st.session_state.httpx_cookies.get('OmniPDFSession')}")
            
            try:
                logger.info(f"FDecode JSON from response: {response}")
                logger.info(f"Decode JSON from headers: {response.headers}")
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from response: {response.text}: {e}")
                server_status.error("Received an invalid response from the server.")
                return "Sorry, I received an invalid response from the server."
            
            # Use the decoded data for all subsequent checks
            if "detail" in data:
                server_status.info(data["detail"])
                logger.info(f"Info details: {data['detail']}")
            else:
                server_status.success("Successfully generated response")
                logger.info(f"Chat response: {data}")

            if response.status_code == 201:
                return data["response"]
            elif response.status_code == 202:
                # Still processing, continue polling
                if attempt < max_retries - 1:
                    chat_status.info(f"Generating response... (attempt {attempt + 1}/{max_retries})")
                    if "detail" in data:
                        server_status.info(data["detail"])
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise TimeoutError("Response generation timed out after maximum retries")
            elif response.status_code == 404:
                server_status.error("Documents not found or not embedded yet")
                st.error(f"{response.json()}")
                return "Sorry, the documents you selected haven't been embedded yet. Please go to the Images page and wait for embedding to complete, then try again."
            else:
                # Handle other HTTP errors
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                server_status.error(f"Server error: {response.status_code}")
                return f"Sorry, there was an error: {response.status_code}"
                
        except httpx.RequestError as e:
            logger.error(f"Request error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                server_status.error("Failed to connect to chat service")
                return "Sorry, I couldn't connect to the chat service."
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            server_status.error(f"Unexpected error: {str(e)}")
            return "Sorry, an unexpected error occurred."

    server_status.error("Max retries exceeded")
    return "Sorry, the request timed out. Please try again."

def simulate_rag_response(prompt, _document_content):
    # Placeholder response - replace with your actual RAG implementation
    return f"This is a simulated response for: {prompt}"

# Check if documents are available
if "processed_data" not in st.session_state or not st.session_state.processed_data:
    st.info("No documents available. Please upload and process documents first.")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        file_options = {}
        if "processed_data" in st.session_state and st.session_state.processed_data:
            logger.info(f"Processed data structure: {st.session_state.processed_data}")
            # Create a mapping of filenames to doc_ids
            for temp_doc_id, doc_data in st.session_state.processed_data.items():
                filename = doc_data.get('uploaded_filename', temp_doc_id)
                # Use the actual doc_id from the response, not the temp_doc_id
                actual_doc_id = doc_data.get('doc_id', temp_doc_id)
                file_options[filename] = actual_doc_id
                logger.info(f"Mapping {filename} -> {actual_doc_id} (temp_id: {temp_doc_id})")

        selected_files = st.multiselect(
            "Select files:",
            options=list(file_options.keys()) if file_options else [],
            default=list(file_options.keys()) if file_options else [],
            key="file_selector"
        )

        logger.info(f"Selected files: {selected_files}")

        # Update doc_ids based on selected filenames
        doc_ids = []
        if selected_files and file_options:
            doc_ids = [file_options[filename] for filename in selected_files]
            logger.info(f"Mapped doc_ids: {doc_ids}")
            logger.info(f"File options mapping: {file_options}")

    with col2:
        # Create sub-columns for side-by-side buttons
        btn_col1, btn_col2, btn_col3 = st.columns(3)

        with btn_col1:
            if st.button("Summarize", key="summary_btn"):
                if not doc_ids:
                    st.error("Please select at least one document to summarize.")
                else:
                    prompt = "Summarize the document"
                    response = runner.run(chat_with_rag(prompt, doc_ids))
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
        
        with btn_col2:    
            if st.button("Main Topic", key="topic_btn"):
                if not doc_ids:
                    st.error("Please select at least one document to analyze.")
                else:
                    prompt = "What is the main topic?"
                    response = runner.run(chat_with_rag(prompt, doc_ids))
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
        
        with btn_col3:
            if st.button("Key Findings", key="findings_btn"):
                if not doc_ids:
                    st.error("Please select at least one document to analyze.")
                else:
                    prompt = "What are the key findings?"
                    response = runner.run(chat_with_rag(prompt, doc_ids))
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()

# Chat input
if prompt := st.chat_input("Ask about the document"):
    # Check if any documents are selected
    if not doc_ids:
        st.error("Please select at least one document to chat with.")
    else:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Generate and display assistant response
        response = asyncio.run(chat_with_rag(prompt, doc_ids))

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Rerun to update the interface
        st.rerun()

