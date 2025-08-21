import streamlit as st
import logging
import asyncio
import httpx
import os

CHAT_URL = os.getenv("CHAT_URL", "http://chat_service:8000")
logger = logging.getLogger(__name__)

st.header("Chat")
st.markdown("💬 Ask questions about the document content")

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
    
# WIP, this function is not working, simulate_rag_response is a placeholder
async def chat_with_rag(prompt, _document_content):
    """
    Simulate a RAG response for the given prompt.
    Replace this with actual RAG implementation.
    """
    async with httpx.AsyncClient(cookies=st.session_state.httpx_cookies) as client:
        response = await client.post(url=f"{CHAT_URL}/chat/",
                                     json={"prompt": prompt})
        if response.status_code == 200:
            return response.json()  # Job done, return result
        else:
            logger.error(f"Error in chat_with_rag: {response.status_code} - {response.text}")

def simulate_rag_response(prompt, _document_content):
    # Placeholder response - replace with your actual RAG implementation
    return prompt

# Suggested questions
st.text("💡 Suggested Questions")
col1, col2 = st.columns(2)

with col1:
    if st.button("What is the main topic?"):
        response = asyncio.run(chat_with_rag("What is the main topic?", "document content"))
        st.session_state.messages.append({"role": "user", "content": "What is the main topic?"})
        st.session_state.messages.append({"role": "assistant", "content": response})
        # Rerun to update the interface
        st.rerun()
        
    if st.button("Who are the authors?"):
        response = simulate_rag_response("Who are the authors?", "document content")
        st.session_state.messages.append({"role": "user", "content": "Who are the authors?"})
        st.session_state.messages.append({"role": "assistant", "content": response})
        # Rerun to update the interface
        st.rerun()

with col2:
    if st.button("Summarize the document"):
        response = simulate_rag_response("Summarize the document", "document content")
        st.session_state.messages.append({"role": "user", "content": "Summarize the document"})
        st.session_state.messages.append({"role": "assistant", "content": response})
        # Rerun to update the interface
        st.rerun()
    
    if st.button("What are the key findings?"):
        response = simulate_rag_response("What are the key findings?", "document content")
        st.session_state.messages.append({"role": "user", "content": "What are the key findings?"})
        st.session_state.messages.append({"role": "assistant", "content": response})
        # Rerun to update the interface
        st.rerun()

# Chat input
if prompt := st.chat_input("Ask about the document"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generate and display assistant response
    response = simulate_rag_response(prompt, "document content")
    response2 = asyncio.run(chat_with_rag(prompt, "document content"))
    

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.messages.append({"role": "assistant", "content": response2})

    # Rerun to update the interface
    st.rerun()