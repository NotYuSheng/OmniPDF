import pytest
from pydantic import ValidationError
from models.render import (
    DocumentRendererResponse,
    DoclingTranslationResponse,
    AnnotationResponse,
)
from models.bypass import BypassResponse


class TestDocumentRendererResponse:
    def test_valid_document_renderer_response(self):
        """Test creation of valid DocumentRendererResponse"""
        response = DocumentRendererResponse(
            doc_id="doc123",
            filename="doc123/rendered.pdf",
            download_url="https://example.com/download/doc123",
        )

        assert response.doc_id == "doc123"
        assert response.filename == "doc123/rendered.pdf"
        assert str(response.download_url) == "https://example.com/download/doc123"

    def test_document_renderer_response_without_url(self):
        """Test DocumentRendererResponse without download_url"""
        response = DocumentRendererResponse(
            doc_id="doc123", filename="doc123/rendered.pdf"
        )

        assert response.doc_id == "doc123"
        assert response.filename == "doc123/rendered.pdf"
        assert response.download_url is None

    def test_invalid_document_renderer_response_missing_doc_id(self):
        """Test DocumentRendererResponse validation without doc_id"""
        with pytest.raises(ValidationError):
            DocumentRendererResponse(filename="doc123/rendered.pdf")

    def test_invalid_document_renderer_response_missing_filename(self):
        """Test DocumentRendererResponse validation without filename"""
        with pytest.raises(ValidationError):
            DocumentRendererResponse(doc_id="doc123")

    def test_invalid_document_renderer_response_invalid_url(self):
        """Test DocumentRendererResponse with invalid URL"""
        with pytest.raises(ValidationError):
            DocumentRendererResponse(
                doc_id="doc123",
                filename="doc123/rendered.pdf",
                download_url="not-a-valid-url",
            )


class TestDoclingTranslationResponse:
    def test_valid_docling_translation_response(self):
        """Test creation of valid DoclingTranslationResponse"""
        response = DoclingTranslationResponse(
            schema_name="test_schema",
            version="1.0",
            name="test_document",
            origin={"source": "test"},
            furniture={"tables": []},
            texts=[{"text": "sample text"}],
            pictures=[{"image": "base64"}],
            tables=[{"table_data": []}],
            key_value_items=[{"key": "value"}],
            form_items=[{"field": "input"}],
            pages={"total": 1},
        )

        assert response.schema_name == "test_schema"
        assert response.version == "1.0"
        assert response.name == "test_document"
        assert len(response.texts) == 1
        assert len(response.pictures) == 1
        assert len(response.tables) == 1

    def test_docling_translation_response_empty_dicts_lists(self):
        """Test DoclingTranslationResponse with empty dicts and lists"""
        response = DoclingTranslationResponse(
            schema_name="test_schema",
            version="1.0",
            name="test_document",
            origin={},
            furniture={},
            texts=[],
            pictures=[],
            tables=[],
            key_value_items=[],
            form_items=[],
            pages={},
        )

        assert response.texts == []
        assert response.pictures == []
        assert response.tables == []
        assert response.origin == {}
        assert response.furniture == {}
        assert response.pages == {}

    def test_invalid_docling_translation_response_missing_required(self):
        """Test DoclingTranslationResponse validation without required fields"""
        with pytest.raises(ValidationError):
            DoclingTranslationResponse(
                schema_name="test_schema",
                version="1.0",
                # Missing required fields
            )


class TestAnnotationResponse:
    def test_valid_annotation_response(self):
        """Test creation of valid AnnotationResponse"""
        docling_data = DoclingTranslationResponse(
            schema_name="test_schema",
            version="1.0",
            name="test_document",
            origin={},
            furniture={},
            texts=[],
            pictures=[],
            tables=[],
            key_value_items=[],
            form_items=[],
            pages={},
        )

        response = AnnotationResponse(
            doc_id="doc123",
            docling=docling_data,
            source_lang="Spanish",
            target_lang="English",
        )

        assert response.doc_id == "doc123"
        assert response.source_lang == "Spanish"
        assert response.target_lang == "English"
        assert response.docling is not None

    def test_annotation_response_without_docling(self):
        """Test AnnotationResponse without docling data"""
        response = AnnotationResponse(
            doc_id="doc123", source_lang="Spanish", target_lang="English"
        )

        assert response.doc_id == "doc123"
        assert response.docling is None
        assert response.source_lang == "Spanish"
        assert response.target_lang == "English"

    def test_invalid_annotation_response_missing_required(self):
        """Test AnnotationResponse validation without required fields"""
        with pytest.raises(ValidationError):
            AnnotationResponse(
                doc_id="doc123",
                source_lang="Spanish",
                # Missing target_lang
            )


class TestBypassResponse:
    def test_valid_bypass_response(self):
        """Test creation of valid BypassResponse"""
        response = BypassResponse(
            doc_id="doc123",
            filename="doc123/original.json",
            download_url="https://example.com/download/doc123",
        )

        assert response.doc_id == "doc123"
        assert response.filename == "doc123/original.json"
        assert str(response.download_url) == "https://example.com/download/doc123"

    def test_bypass_response_without_url(self):
        """Test BypassResponse without download_url"""
        response = BypassResponse(doc_id="doc123", filename="doc123/original.json")

        assert response.doc_id == "doc123"
        assert response.filename == "doc123/original.json"
        assert response.download_url is None

    def test_invalid_bypass_response_missing_doc_id(self):
        """Test BypassResponse validation without doc_id"""
        with pytest.raises(ValidationError):
            BypassResponse(filename="doc123/original.json")

    def test_invalid_bypass_response_missing_filename(self):
        """Test BypassResponse validation without filename"""
        with pytest.raises(ValidationError):
            BypassResponse(doc_id="doc123")

    def test_invalid_bypass_response_invalid_url(self):
        """Test BypassResponse with invalid URL"""
        with pytest.raises(ValidationError):
            BypassResponse(
                doc_id="doc123",
                filename="doc123/original.json",
                download_url="invalid-url",
            )
