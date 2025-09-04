import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from models.chat import ChatRequest
from routers.chat import prepare_retrieval_results, rerank_chunks, perform_rag_query
from shared_utils.openai_client import get_openai_client


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_chat_request():
    return ChatRequest(
        message="What is the main topic of the document?",
        collection_name="test_collection",
        doc_id=None,
    )


@pytest.fixture
def sample_chroma_results():
    return {
        "documents": [["Sample document content", "Another document chunk"]],
        "metadatas": [[{"doc_id": "doc1", "page": 1}, {"doc_id": "doc2", "page": 2}]],
        "distances": [[0.1, 0.3]],
        "ids": [["chunk1", "chunk2"]],
    }


class TestPrepareRetrievalResults:
    def test_empty_results(self):
        """Test handling of empty ChromaDB results"""
        result = prepare_retrieval_results({})
        assert result == []

        result = prepare_retrieval_results({"documents": []})
        assert result == []

    def test_valid_results(self, sample_chroma_results):
        """Test processing of valid ChromaDB results"""
        chunks = prepare_retrieval_results(sample_chroma_results)

        assert len(chunks) == 2
        assert chunks[0]["content"] == "Sample document content"
        assert chunks[0]["chunk_id"] == "chunk1"
        assert chunks[0]["doc_id"] == "doc1"
        assert (
            0 < chunks[0]["similarity_score"] <= 1
        )  # L2 distance converted to similarity

        assert chunks[1]["content"] == "Another document chunk"
        assert chunks[1]["chunk_id"] == "chunk2"
        assert chunks[1]["doc_id"] == "doc2"

    def test_similarity_filtering(self, sample_chroma_results):
        """Test filtering by minimum similarity score"""
        with patch("routers.chat.rag_config") as mock_config:
            mock_config.min_similarity_score = 0.8
            chunks = prepare_retrieval_results(sample_chroma_results)

            # With high similarity threshold, some chunks should be filtered
            high_similarity_chunks = [c for c in chunks if c["similarity_score"] >= 0.8]
            assert len(chunks) >= len(high_similarity_chunks)


class TestRerankChunks:
    @pytest.mark.asyncio
    async def test_empty_chunks(self):
        """Test reranking with empty chunks list"""
        result = await rerank_chunks([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_document_chunks(self):
        """Test reranking chunks from single document"""
        chunks = [
            {"doc_id": "doc1", "similarity_score": 0.9},
            {"doc_id": "doc1", "similarity_score": 0.7},
            {"doc_id": "doc1", "similarity_score": 0.8},
        ]

        reranked = await rerank_chunks(chunks)

        # Should be sorted by similarity score within the document
        assert len(reranked) == 3
        assert reranked[0]["similarity_score"] == 0.9
        assert reranked[1]["similarity_score"] == 0.8
        assert reranked[2]["similarity_score"] == 0.7

    @pytest.mark.asyncio
    async def test_multiple_document_chunks(self):
        """Test reranking chunks from multiple documents"""
        chunks = [
            {"doc_id": "doc1", "similarity_score": 0.9},
            {"doc_id": "doc2", "similarity_score": 0.85},
            {"doc_id": "doc1", "similarity_score": 0.7},
            {"doc_id": "doc2", "similarity_score": 0.6},
        ]

        reranked = await rerank_chunks(chunks)

        # Should interleave documents, highest similarity first from each doc
        assert len(reranked) == 4
        assert (
            reranked[0]["doc_id"] == "doc1" and reranked[0]["similarity_score"] == 0.9
        )
        assert (
            reranked[1]["doc_id"] == "doc2" and reranked[1]["similarity_score"] == 0.85
        )


class TestPerformRAGQuery:
    @pytest.mark.asyncio
    async def test_no_chunks_found(self):
        """Test RAG query when no relevant chunks are found"""
        with (
            patch("routers.chat.get_chroma_client") as mock_chroma,
            patch("routers.chat.prepare_retrieval_results") as mock_prepare,
        ):
            mock_collection = AsyncMock()
            mock_collection.query.return_value = {}
            mock_chroma.return_value.get_collection.return_value = mock_collection
            mock_prepare.return_value = []

            result = await perform_rag_query(
                query="test query",
                collection_name="test_collection",
                top_k=5,
                openai_client=AsyncMock(),
            )

            user_prompt, chunks, system_prompt, query_type = result
            assert "couldn't find any relevant information" in user_prompt
            assert chunks == []
            assert query_type == "general"

    @pytest.mark.asyncio
    async def test_successful_rag_query(self, sample_chroma_results):
        """Test successful RAG query execution"""
        mock_chunks = [
            {"content": "test content", "similarity_score": 0.9, "doc_id": "doc1"}
        ]

        with (
            patch("routers.chat.get_chroma_client") as mock_chroma,
            patch("routers.chat.prepare_retrieval_results") as mock_prepare,
            patch("routers.chat.rag_optimizer") as mock_optimizer,
            patch("routers.chat.prompt_templates") as mock_templates,
        ):
            mock_collection = AsyncMock()
            mock_collection.query.return_value = sample_chroma_results
            mock_chroma.return_value.get_collection.return_value = mock_collection
            mock_prepare.return_value = mock_chunks

            mock_optimizer.chunk_optimization.return_value = (
                mock_chunks,
                "test context",
            )
            # Make detect_query_type async mock
            mock_optimizer.detect_query_type = AsyncMock(return_value="summary")

            mock_templates.get_system_prompt.return_value = "system prompt"
            mock_templates.format_user_prompt.return_value = "user prompt"

            result = await perform_rag_query(
                query="test query",
                collection_name="test_collection",
                top_k=5,
                openai_client=AsyncMock(),
            )

            user_prompt, chunks, system_prompt, query_type = result
            assert user_prompt == "user prompt"
            assert chunks == mock_chunks
            assert system_prompt == "system prompt"
            assert query_type == "summary"


class TestChatEndpoint:
    def test_invalid_query_validation(self, sample_chat_request):
        """Test chat endpoint with invalid query"""
        with patch("routers.chat.validate_query_with_llm") as mock_validate:
            mock_validate.return_value = (False, "Query is too vague")

            # Mock the OpenAI client dependency
            mock_ai_client = AsyncMock()

            # Use FastAPI TestClient with dependency override
            test_client = TestClient(app)
            test_client.app.dependency_overrides[get_openai_client] = (
                lambda: mock_ai_client
            )

            try:
                response = test_client.post(
                    "/chat/chat/",  # Router prefix + endpoint
                    json=sample_chat_request.model_dump(),
                )

                assert response.status_code == 201
                data = response.json()
                assert "couldn't process your query" in data["response"]
                assert data["metadata"]["rag_performed"] is False
                assert data["relevant_chunks"] == []
            finally:
                # Clean up dependency overrides
                test_client.app.dependency_overrides.clear()

    def test_successful_chat_response(self, sample_chat_request):
        """Test successful chat endpoint response"""
        mock_chunks = [{"content": "test", "doc_id": "doc1"}]
        mock_openai_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "This is the AI response"
        mock_choice.message = mock_message
        mock_openai_response.choices = [mock_choice]

        with (
            patch("routers.chat.validate_query_with_llm") as mock_validate,
            patch("routers.chat.perform_rag_query") as mock_rag,
        ):
            mock_validate.return_value = (True, None)
            mock_rag.return_value = (
                "user prompt",
                mock_chunks,
                "system prompt",
                "general",
            )

            # Mock the OpenAI client directly in the dependency
            mock_ai_client = AsyncMock()
            mock_ai_client.chat.completions.create.return_value = mock_openai_response

            # Use FastAPI TestClient with dependency override
            test_client = TestClient(app)
            test_client.app.dependency_overrides[get_openai_client] = (
                lambda: mock_ai_client
            )

            try:
                response = test_client.post(
                    "/chat/chat/",  # Router prefix + endpoint
                    json=sample_chat_request.model_dump(),
                )

                assert response.status_code == 201
                data = response.json()
                # The response may be post-processed and have a period added
                assert "This is the AI response" in data["response"]
                assert data["metadata"]["rag_performed"] is True
                assert len(data["relevant_chunks"]) == 1
            finally:
                # Clean up dependency overrides
                test_client.app.dependency_overrides.clear()

    def test_openai_api_error(self, sample_chat_request):
        """Test handling of OpenAI API errors"""
        # Create a real APIError by importing it
        from openai import APIError
        import httpx

        mock_chunks = [{"content": "test", "doc_id": "doc1"}]
        mock_request = httpx.Request("POST", "http://test")

        with (
            patch("routers.chat.validate_query_with_llm") as mock_validate,
            patch("routers.chat.perform_rag_query") as mock_rag,
        ):
            mock_validate.return_value = (True, None)
            mock_rag.return_value = ("prompt", mock_chunks, "system", "general")

            # Mock the OpenAI client to raise a real APIError
            mock_ai_client = AsyncMock()
            api_error = APIError("API Error", request=mock_request, body=None)
            mock_ai_client.chat.completions.create.side_effect = api_error

            # Use FastAPI TestClient with dependency override
            test_client = TestClient(app)
            test_client.app.dependency_overrides[get_openai_client] = (
                lambda: mock_ai_client
            )

            try:
                response = test_client.post(
                    "/chat/chat/",  # Router prefix + endpoint
                    json=sample_chat_request.model_dump(),
                )

                assert response.status_code == 500
                data = response.json()
                assert "Unexpected error during chat completion" in data["detail"]
            finally:
                # Clean up dependency overrides
                test_client.app.dependency_overrides.clear()
