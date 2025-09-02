import pytest
from pydantic import ValidationError
from models.translate import DoclingTranslationResponse, TranslateResponse


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
            pages={"total": 1}
        )
        
        assert response.schema_name == "test_schema"
        assert response.version == "1.0"
        assert response.name == "test_document"
        assert len(response.texts) == 1
        assert len(response.pictures) == 1
        assert len(response.tables) == 1

    def test_docling_translation_response_empty_lists(self):
        """Test DoclingTranslationResponse with empty lists"""
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
            pages={}
        )
        
        assert response.texts == []
        assert response.pictures == []
        assert response.tables == []
        assert response.key_value_items == []
        assert response.form_items == []

    def test_invalid_docling_translation_response_missing_required(self):
        """Test DoclingTranslationResponse validation without required fields"""
        with pytest.raises(ValidationError):
            DoclingTranslationResponse(
                schema_name="test_schema",
                version="1.0"
                # Missing required fields
            )


class TestTranslateResponse:
    def test_valid_translate_response(self):
        """Test creation of valid TranslateResponse"""
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
            pages={}
        )
        
        response = TranslateResponse(
            doc_id="doc123",
            docling=docling_data,
            source_lang="Spanish",
            target_lang="English"
        )
        
        assert response.doc_id == "doc123"
        assert response.source_lang == "Spanish"
        assert response.target_lang == "English"
        assert response.docling is not None

    def test_translate_response_without_docling(self):
        """Test TranslateResponse without docling data"""
        response = TranslateResponse(
            doc_id="doc123",
            source_lang="Spanish",
            target_lang="English"
        )
        
        assert response.doc_id == "doc123"
        assert response.docling is None
        assert response.source_lang == "Spanish"
        assert response.target_lang == "English"

    def test_invalid_translate_response_missing_doc_id(self):
        """Test TranslateResponse validation without doc_id"""
        with pytest.raises(ValidationError):
            TranslateResponse(
                source_lang="Spanish",
                target_lang="English"
            )

    def test_invalid_translate_response_missing_source_lang(self):
        """Test TranslateResponse validation without source_lang"""
        with pytest.raises(ValidationError):
            TranslateResponse(
                doc_id="doc123",
                target_lang="English"
            )

    def test_invalid_translate_response_missing_target_lang(self):
        """Test TranslateResponse validation without target_lang"""
        with pytest.raises(ValidationError):
            TranslateResponse(
                doc_id="doc123",
                source_lang="Spanish"
            )

    def test_translate_response_empty_strings(self):
        """Test TranslateResponse with empty string values"""
        with pytest.raises(ValidationError):
            TranslateResponse(
                doc_id="",
                source_lang="Spanish",
                target_lang="English"
            )
