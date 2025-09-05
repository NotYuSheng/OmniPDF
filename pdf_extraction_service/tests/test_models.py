import pytest
from pydantic import ValidationError
from models.extractor import PDFDataResponse, ExtractResponse


class TestPDFDataResponse:
    def test_valid_pdf_data_response(self):
        """Test creation of valid PDFDataResponse"""
        data = PDFDataResponse(
            schema_name="docling",
            version="1.0",
            name="test.pdf",
            origin={"filename": "test.pdf"},
            furniture={},
            texts=[{"content": "Sample text"}],
            pictures=[{"image": {"uri": "test"}}],
            tables=[],
            key_value_items=[],
            form_items=[],
            pages={"0": {"image": {"uri": "page"}}},
        )

        assert data.schema_name == "docling"
        assert data.version == "1.0"
        assert data.name == "test.pdf"
        assert len(data.texts) == 1
        assert len(data.pictures) == 1

    def test_pdf_data_response_empty_lists(self):
        """Test PDFDataResponse with empty lists"""
        data = PDFDataResponse(
            schema_name="docling",
            version="1.0",
            name="test.pdf",
            origin={},
            furniture={},
            texts=[],
            pictures=[],
            tables=[],
            key_value_items=[],
            form_items=[],
            pages={},
        )

        assert data.texts == []
        assert data.pictures == []
        assert data.tables == []

    def test_invalid_pdf_data_response_missing_required(self):
        """Test PDFDataResponse validation with missing required fields"""
        with pytest.raises(ValidationError):
            PDFDataResponse()  # Missing all required fields

    def test_invalid_pdf_data_response_wrong_type(self):
        """Test PDFDataResponse validation with wrong field types"""
        with pytest.raises(ValidationError):
            PDFDataResponse(
                schema_name="docling",
                version="1.0",
                name="test.pdf",
                origin={},
                furniture={},
                texts="not a list",  # Should be list
                pictures=[],
                tables=[],
                key_value_items=[],
                form_items=[],
                pages={},
            )


class TestExtractResponse:
    def test_valid_extract_response_processing(self):
        """Test creation of valid ExtractResponse in processing state"""
        response = ExtractResponse(doc_id="test123", status="processing")

        assert response.doc_id == "test123"
        assert response.status == "processing"
        assert response.result is None

    def test_valid_extract_response_completed(self):
        """Test creation of valid ExtractResponse with result"""
        pdf_data = PDFDataResponse(
            schema_name="docling",
            version="1.0",
            name="test.pdf",
            origin={},
            furniture={},
            texts=[],
            pictures=[],
            tables=[],
            key_value_items=[],
            form_items=[],
            pages={},
        )

        response = ExtractResponse(
            doc_id="test123", status="completed", result=pdf_data
        )

        assert response.doc_id == "test123"
        assert response.status == "completed"
        assert response.result is not None
        assert response.result.schema_name == "docling"

    def test_extract_response_failed_status(self):
        """Test ExtractResponse with failed status"""
        response = ExtractResponse(doc_id="test123", status="failed")

        assert response.doc_id == "test123"
        assert response.status == "failed"
        assert response.result is None

    def test_invalid_extract_response_no_doc_id(self):
        """Test ExtractResponse validation without doc_id"""
        with pytest.raises(ValidationError):
            ExtractResponse(status="processing")

    def test_invalid_extract_response_no_status(self):
        """Test ExtractResponse validation without status"""
        with pytest.raises(ValidationError):
            ExtractResponse(doc_id="test123")
