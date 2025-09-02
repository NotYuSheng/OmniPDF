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

async def chat_with_rag(prompt: str, doc_id: str = None, max_retries: int = 600, delay: int = 1):
    """
    Send chat request to RAG backend and handle the response.
    """
    for attempt in range(max_retries):
        try:
            response = await client.post(url=f"{CHAT_URL}/chat/chat/",
                                        json={"message": prompt,
                                              "doc_id": doc_id,
                                              "collection_name": "default_collection"
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

# Get document ID from session state
if "processed_data" in st.session_state and st.session_state.processed_data is not None:
    if "doc_id" in st.session_state.processed_data:
        doc_id = st.session_state.processed_data.get("doc_id")
        if not doc_id:
            st.warning("No document ID found. Please upload and process a document first.")
    else:
        st.warning("No document ID found. Please upload and process a document first.")
else:
    st.warning("No document processed. Please upload and process a document first.")

# Suggested questions
st.text("💡 Suggested Questions")
col1, col2 = st.columns(2)

with col1:
    if st.button("What is the main topic?"):
        prompt = "What is the main topic?"
        response = runner.run(chat_with_rag(prompt))
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
        
    if st.button("Who are the authors?"):
        prompt = "Who are the authors?"
        response = runner.run(chat_with_rag(prompt, doc_id))
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

with col2:
    if st.button("Summarize the document"):
        prompt = "Summarize the document"
        response = runner.run(chat_with_rag(prompt, doc_id))
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    if st.button("What are the key findings?"):
        prompt = "What are the key findings?"
        response = runner.run(chat_with_rag(prompt, doc_id))
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

# Chat input
if prompt := st.chat_input("Ask about the document"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generate and display assistant response
    response = asyncio.run(chat_with_rag(prompt, doc_id))

    response = response.json()
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

    # Rerun to update the interface
    st.rerun()
