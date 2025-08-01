import streamlit as st
import logging
import asyncio
import httpx
import os

CHAT_URL = os.getenv("CHAT_URL", "http://chat_service:8000")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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