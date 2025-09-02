import pytest
from pydantic import ValidationError
from models.chat import ChatRequest, ChatResponse


class TestChatRequest:
    def test_valid_chat_request(self):
        """Test creation of valid ChatRequest"""
        request = ChatRequest(
            message="What is this document about?",
            collection_name="test_collection"
        )
        
        assert request.message == "What is this document about?"
        assert request.collection_name == "test_collection"
        assert request.doc_id is None

    def test_chat_request_with_doc_id(self):
        """Test ChatRequest with optional doc_id"""
        request = ChatRequest(
            message="What is this document about?",
            collection_name="test_collection",
            doc_id="doc123"
        )
        
        assert request.doc_id == "doc123"

    def test_chat_request_default_collection(self):
        """Test ChatRequest with default collection name"""
        request = ChatRequest(message="Test message")
        assert request.collection_name == "default_collection"

    def test_chat_request_empty_message_allowed(self):
        """Test ChatRequest allows empty message (Pydantic v2 behavior)"""
        # In Pydantic v2, empty strings are valid unless explicitly constrained
        request = ChatRequest(message="", collection_name="test")
        assert request.message == ""
        assert request.collection_name == "test"

    def test_invalid_chat_request_no_message(self):
        """Test ChatRequest validation without message"""
        with pytest.raises(ValidationError):
            ChatRequest(collection_name="test")


class TestChatResponse:
    def test_valid_chat_response(self):
        """Test creation of valid ChatResponse"""
        response = ChatResponse(
            response="This is the AI response",
            metadata={"model": "gpt-4", "tokens": 100}
        )
        
        assert response.response == "This is the AI response"
        assert response.metadata == {"model": "gpt-4", "tokens": 100}
        assert response.relevant_chunks == []

    def test_chat_response_with_chunks(self):
        """Test ChatResponse with relevant chunks"""
        chunks = [
            {"content": "chunk1", "similarity": 0.9},
            {"content": "chunk2", "similarity": 0.8}
        ]
        
        response = ChatResponse(
            response="AI response",
            relevant_chunks=chunks,
            metadata={"model": "gpt-4"}
        )
        
        assert len(response.relevant_chunks) == 2
        assert response.relevant_chunks[0]["content"] == "chunk1"

    def test_invalid_chat_response_no_response(self):
        """Test ChatResponse validation without response"""
        with pytest.raises(ValidationError):
            ChatResponse(metadata={"model": "gpt-4"})

    def test_invalid_chat_response_no_metadata(self):
        """Test ChatResponse validation without metadata"""
        with pytest.raises(ValidationError):
            ChatResponse(response="AI response")
