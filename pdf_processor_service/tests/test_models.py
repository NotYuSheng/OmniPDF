import pytest
from pydantic import ValidationError
from models.session import SessionResponse, SessionDataResponse
from models.document import DocumentUploadResponse
from models.text_chunks import TextChunkData, TextChunksResponse
from models.images import ImageData, ImageResponse
from models.tables import TableData, TablesResponse


class TestSessionResponse:
    def test_valid_session_response(self):
        """Test creation of valid SessionResponse"""
        response = SessionResponse(session_id="session123", valid_session=True)

        assert response.session_id == "session123"
        assert response.valid_session is True

    def test_session_response_invalid_session(self):
        """Test SessionResponse with invalid session"""
        response = SessionResponse(session_id="session123", valid_session=False)

        assert response.session_id == "session123"
        assert response.valid_session is False

    def test_invalid_session_response_missing_session_id(self):
        """Test SessionResponse validation without session_id"""
        with pytest.raises(ValidationError):
            SessionResponse(valid_session=True)

    def test_invalid_session_response_missing_valid_session(self):
        """Test SessionResponse validation without valid_session"""
        with pytest.raises(ValidationError):
            SessionResponse(session_id="session123")


class TestSessionDataResponse:
    def test_valid_session_data_response(self):
        """Test creation of valid SessionDataResponse"""
        response = SessionDataResponse(
            session_id="session123", session_data=["doc1", "doc2", "doc3"]
        )

        assert response.session_id == "session123"
        assert len(response.session_data) == 3
        assert "doc1" in response.session_data

    def test_session_data_response_empty_data(self):
        """Test SessionDataResponse with empty session data"""
        response = SessionDataResponse(session_id="session123", session_data=[])

        assert response.session_id == "session123"
        assert response.session_data == []

    def test_invalid_session_data_response_missing_fields(self):
        """Test SessionDataResponse validation without required fields"""
        with pytest.raises(ValidationError):
            SessionDataResponse(session_id="session123")


class TestDocumentUploadResponse:
    def test_valid_document_upload_response(self):
        """Test creation of valid DocumentUploadResponse"""
        response = DocumentUploadResponse(
            doc_id="doc123",
            filename="document.pdf",
            download_url="https://example.com/download/doc123",
        )

        assert response.doc_id == "doc123"
        assert response.filename == "document.pdf"
        assert str(response.download_url) == "https://example.com/download/doc123"

    def test_document_upload_response_without_url(self):
        """Test DocumentUploadResponse without download_url"""
        response = DocumentUploadResponse(doc_id="doc123", filename="document.pdf")

        assert response.doc_id == "doc123"
        assert response.filename == "document.pdf"
        assert response.download_url is None

    def test_invalid_document_upload_response_missing_required(self):
        """Test DocumentUploadResponse validation without required fields"""
        with pytest.raises(ValidationError):
            DocumentUploadResponse(filename="document.pdf")

    def test_invalid_document_upload_response_invalid_url(self):
        """Test DocumentUploadResponse with invalid URL"""
        with pytest.raises(ValidationError):
            DocumentUploadResponse(
                doc_id="doc123", filename="document.pdf", download_url="not-a-valid-url"
            )


class TestTextChunkData:
    def test_valid_text_chunk_data(self):
        """Test creation of valid TextChunkData"""
        chunk = TextChunkData(
            chunk_id=1, page=5, chunk="This is a text chunk from the document."
        )

        assert chunk.chunk_id == 1
        assert chunk.page == 5
        assert chunk.chunk == "This is a text chunk from the document."

    def test_invalid_text_chunk_data_missing_fields(self):
        """Test TextChunkData validation without required fields"""
        with pytest.raises(ValidationError):
            TextChunkData(chunk_id=1, page=5)


class TestTextChunksResponse:
    def test_valid_text_chunks_response(self):
        """Test creation of valid TextChunksResponse"""
        chunks = [
            TextChunkData(chunk_id=1, page=1, chunk="First chunk"),
            TextChunkData(chunk_id=2, page=1, chunk="Second chunk"),
        ]

        response = TextChunksResponse(
            doc_id="doc123", filename="document.pdf", chunks=chunks
        )

        assert response.doc_id == "doc123"
        assert response.filename == "document.pdf"
        assert len(response.chunks) == 2
        assert response.chunks[0].chunk_id == 1

    def test_text_chunks_response_empty_chunks(self):
        """Test TextChunksResponse with empty chunks"""
        response = TextChunksResponse(
            doc_id="doc123", filename="document.pdf", chunks=[]
        )

        assert response.doc_id == "doc123"
        assert response.chunks == []

    def test_invalid_text_chunks_response_missing_fields(self):
        """Test TextChunksResponse validation without required fields"""
        with pytest.raises(ValidationError):
            TextChunksResponse(doc_id="doc123", chunks=[])


class TestImageData:
    def test_valid_image_data(self):
        """Test creation of valid ImageData"""
        image = ImageData(
            image_key="doc123/image1.png",
            url="https://example.com/images/doc123/image1.png",
        )

        assert image.image_key == "doc123/image1.png"
        assert image.url == "https://example.com/images/doc123/image1.png"

    def test_invalid_image_data_missing_fields(self):
        """Test ImageData validation without required fields"""
        with pytest.raises(ValidationError):
            ImageData(image_key="doc123/image1.png")


class TestImageResponse:
    def test_valid_image_response(self):
        """Test creation of valid ImageResponse"""
        images = [
            ImageData(
                image_key="doc123/image1.png", url="https://example.com/image1.png"
            ),
            ImageData(
                image_key="doc123/image2.png", url="https://example.com/image2.png"
            ),
        ]

        response = ImageResponse(
            doc_id="doc123", filename="document.pdf", images=images
        )

        assert response.doc_id == "doc123"
        assert response.filename == "document.pdf"
        assert len(response.images) == 2
        assert response.images[0].image_key == "doc123/image1.png"

    def test_image_response_empty_images(self):
        """Test ImageResponse with empty images"""
        response = ImageResponse(doc_id="doc123", filename="document.pdf", images=[])

        assert response.doc_id == "doc123"
        assert response.images == []

    def test_invalid_image_response_missing_fields(self):
        """Test ImageResponse validation without required fields"""
        with pytest.raises(ValidationError):
            ImageResponse(doc_id="doc123", images=[])


class TestTableData:
    def test_valid_table_data(self):
        """Test creation of valid TableData"""
        table = TableData(table_id=1, page=3, csv="col1,col2,col3\nval1,val2,val3")

        assert table.table_id == 1
        assert table.page == 3
        assert "col1,col2,col3" in table.csv

    def test_invalid_table_data_missing_fields(self):
        """Test TableData validation without required fields"""
        with pytest.raises(ValidationError):
            TableData(table_id=1, page=3)


class TestTablesResponse:
    def test_valid_tables_response(self):
        """Test creation of valid TablesResponse"""
        tables = [
            TableData(table_id=1, page=1, csv="col1,col2\nval1,val2"),
            TableData(table_id=2, page=2, csv="col3,col4\nval3,val4"),
        ]

        response = TablesResponse(
            doc_id="doc123", filename="document.pdf", tables=tables
        )

        assert response.doc_id == "doc123"
        assert response.filename == "document.pdf"
        assert len(response.tables) == 2
        assert response.tables[0].table_id == 1

    def test_tables_response_empty_tables(self):
        """Test TablesResponse with empty tables"""
        response = TablesResponse(doc_id="doc123", filename="document.pdf", tables=[])

        assert response.doc_id == "doc123"
        assert response.tables == []

    def test_invalid_tables_response_missing_fields(self):
        """Test TablesResponse validation without required fields"""
        with pytest.raises(ValidationError):
            TablesResponse(doc_id="doc123", tables=[])
