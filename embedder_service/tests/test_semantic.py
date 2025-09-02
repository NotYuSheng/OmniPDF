import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
import uuid

from main import app
from models.embed import DataRequest, ProcessingConfig
from routers.semantic import data_chunking


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_config():
    return ProcessingConfig(
        chunk_size=512,
        overlap=50,
        embedding_model="all-MiniLM-L6-v2",
        min_chunk_size=100,
        max_chunk_size=1000
    )


@pytest.fixture
def sample_data_request(sample_config):
    return DataRequest(
        doc_id="test_doc_123",
        session_id="session_456",
        text="This is a sample document text that needs to be chunked and embedded. It contains multiple sentences to test the chunking algorithm properly.",
        config=sample_config,
        pages_info=[]
    )


@pytest.fixture
def mock_chunker():
    mock = MagicMock()
    mock_document = MagicMock()
    mock_document.page_content = "This is a sample chunk"
    mock_document.metadata = {}
    mock.split_documents.return_value = [mock_document]
    return mock


class TestDataChunking:
    @pytest.mark.asyncio
    async def test_successful_chunking(self, sample_data_request):
        """Test successful text chunking"""
        with patch('routers.semantic.get_chunking_model') as mock_get_chunker:
            mock_chunker = MagicMock()
            mock_document = MagicMock()
            mock_document.page_content = "This is a sample chunk"
            mock_document.metadata = {}
            mock_chunker.split_documents.return_value = [mock_document]
            mock_get_chunker.return_value = mock_chunker
            
            result = await data_chunking(sample_data_request)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['content'] == "This is a sample chunk"
            assert result[0]['doc_id'] == "test_doc_123"
            assert result[0]['session_id'] == "session_456"
            assert 'chunk_id' in result[0]
            assert result[0]['chunk_index'] == 0

    @pytest.mark.asyncio
    async def test_empty_text_chunking(self, sample_data_request):
        """Test chunking with empty text raises HTTPException"""
        from fastapi import HTTPException
        
        sample_data_request.text = ""
        
        with pytest.raises(HTTPException) as exc_info:
            await data_chunking(sample_data_request)
        
        assert exc_info.value.status_code == 400
        assert "No textual content found in PDF" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_chunking_multiple_chunks(self, sample_data_request):
        """Test chunking that produces multiple chunks"""
        with patch('routers.semantic.get_chunking_model') as mock_get_chunker:
            mock_chunker = MagicMock()
            mock_docs = []
            for i in range(3):
                mock_doc = MagicMock()
                mock_doc.page_content = f"Chunk content {i+1}"
                mock_doc.metadata = {}
                mock_docs.append(mock_doc)
            
            mock_chunker.split_documents.return_value = mock_docs
            mock_get_chunker.return_value = mock_chunker
            
            result = await data_chunking(sample_data_request)
            
            assert len(result) == 3
            for i, chunk in enumerate(result):
                assert chunk['content'] == f"Chunk content {i+1}"
                assert chunk['chunk_index'] == i
                assert chunk['doc_id'] == "test_doc_123"

    @pytest.mark.asyncio
    async def test_chunking_failure(self, sample_data_request):
        """Test chunking failure handling"""
        from fastapi import HTTPException
        
        with patch('routers.semantic.get_chunking_model') as mock_get_chunker:
            mock_get_chunker.side_effect = Exception("Chunking model error")
            
            with pytest.raises(HTTPException) as exc_info:
                await data_chunking(sample_data_request)
            
            assert exc_info.value.status_code == 500
            assert "Chunking failed" in str(exc_info.value.detail)


class TestSemanticRoutes:
    @pytest.mark.asyncio
    async def test_semantic_embedding_success(self, sample_data_request):
        """Test successful semantic embedding endpoint"""
        mock_chunks = [
            {
                'chunk_id': str(uuid.uuid4()),
                'content': 'Test chunk',
                'chunk_index': 0,
                'start_char': 0,
                'end_char': 10
            }
        ]
        
        mock_embed_results = {
            'status': 'success',
            'chunks_embedded': 1
        }
        
        with patch('routers.semantic.data_chunking') as mock_chunk, \
             patch('routers.semantic.vectorize_chromadb') as mock_vectorize:
            
            mock_chunk.return_value = mock_chunks
            mock_vectorize.return_value = mock_embed_results
            
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/semantic/",
                    json=sample_data_request.dict()
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'success'
            assert data['doc_id'] == 'test_doc_123'
            assert data['chunks_created'] == 1
            assert len(data['chunk_details']) == 1

    @pytest.mark.asyncio
    async def test_semantic_embedding_no_chunks(self, sample_data_request):
        """Test semantic embedding with no chunks created"""
        with patch('routers.semantic.data_chunking') as mock_chunk:
            mock_chunk.return_value = []
            
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/semantic/",
                    json=sample_data_request.dict()
                )
            
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_semantic_embedding_failure(self, sample_data_request):
        """Test semantic embedding endpoint failure"""
        with patch('routers.semantic.data_chunking') as mock_chunk:
            mock_chunk.side_effect = Exception("Embedding failed")
            
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/semantic/",
                    json=sample_data_request.dict()
                )
            
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_verify_document_embedding_found(self):
        """Test document embedding verification when document exists"""
        mock_results = {
            'ids': ['chunk1', 'chunk2'],
            'documents': ['content1', 'content2'],
            'embeddings': [[0.1, 0.2], [0.3, 0.4]]
        }
        
        with patch('routers.semantic.get_chroma_client') as mock_chroma:
            mock_collection = AsyncMock()
            mock_collection.get.return_value = mock_results
            mock_chroma.return_value.get_collection.return_value = mock_collection
            
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.get("/semantic/status/test_doc")
            
            assert response.status_code == 200
            data = response.json()
            assert data['doc_id'] == 'test_doc'
            assert data['status'] == 'found'
            assert data['chunks_found'] == 2
            assert data['chunks_have_embeddings'] is True

    @pytest.mark.asyncio
    async def test_verify_document_embedding_not_found(self):
        """Test document embedding verification when document not found"""
        mock_results = {'ids': []}
        
        with patch('routers.semantic.get_chroma_client') as mock_chroma:
            mock_collection = AsyncMock()
            mock_collection.get.return_value = mock_results
            mock_chroma.return_value.get_collection.return_value = mock_collection
            
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.get("/semantic/status/nonexistent_doc")
            
            assert response.status_code == 200
            data = response.json()
            assert data['doc_id'] == 'nonexistent_doc'
            assert data['status'] == 'not_found'
            assert data['chunks_found'] == 0

    @pytest.mark.asyncio
    async def test_verify_document_embedding_error(self):
        """Test document embedding verification error handling"""
        with patch('routers.semantic.get_chroma_client') as mock_chroma:
            mock_chroma.side_effect = Exception("Database error")
            
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.get("/semantic/status/test_doc")
            
            assert response.status_code == 500