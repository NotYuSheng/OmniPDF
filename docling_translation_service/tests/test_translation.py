import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from routers.translation import router, translate, safe_translate
from models.translate import TranslateResponse, DoclingTranslationResponse
import json


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestTranslateFunction:
    @pytest.mark.asyncio
    @patch("routers.translation.httpx.AsyncClient")
    async def test_translate_success(self, mock_client):
        """Test successful translation"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello world"}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await translate(
            "Hola mundo", source_lang="Spanish", target_lang="English"
        )

        assert result == "Hello world"
        # The function may retry up to 3 times due to its retry logic
        assert mock_client_instance.post.call_count >= 1

    @pytest.mark.asyncio
    @patch("routers.translation.httpx.AsyncClient")
    async def test_translate_auto_detect(self, mock_client):
        """Test translation with auto language detection"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello world"}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await translate("Hola mundo", target_lang="English")

        assert result == "Hello world"
        # Check that the system prompt includes auto-detection language
        call_args = mock_client_instance.post.call_args
        system_message = call_args[1]["json"]["messages"][0]["content"]
        assert "Detect the source language automatically" in system_message

    @pytest.mark.asyncio
    @patch("routers.translation.httpx.AsyncClient")
    async def test_translate_timeout_retry(self, mock_client):
        """Test translation with timeout and retry"""
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(
            side_effect=[
                httpx.ReadTimeout("Timeout"),
                httpx.ReadTimeout("Timeout"),
                MagicMock(
                    json=lambda: {"choices": [{"message": {"content": "Hello"}}]},
                    raise_for_status=MagicMock(),
                ),
            ]
        )
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await translate("Hola", source_lang="Spanish", target_lang="English")

        assert result == "Hello"
        assert mock_client_instance.post.call_count == 3

    @pytest.mark.asyncio
    @patch("routers.translation.httpx.AsyncClient")
    async def test_translate_json_decode_error(self, mock_client):
        """Test translation with JSON decode error"""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await translate("Hola", source_lang="Spanish", target_lang="English")

        assert result is None

    @pytest.mark.asyncio
    @patch("routers.translation.httpx.AsyncClient")
    async def test_translate_key_error(self, mock_client):
        """Test translation with missing keys in response"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "structure"}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await translate("Hola", source_lang="Spanish", target_lang="English")

        assert result is None


class TestSafeTranslateFunction:
    @pytest.mark.asyncio
    @patch("routers.translation.translate")
    async def test_safe_translate_with_text(self, mock_translate):
        """Test safe_translate with text field"""
        mock_translate.return_value = "Translated text"

        entry = {"text": "Original text", "other_field": "value"}
        result = await safe_translate(entry, "Spanish", "English")

        assert result["text"] == "Original text"
        assert result["translated_text"] == "Translated text"
        assert result["other_field"] == "value"
        mock_translate.assert_called_once_with(
            "Original text", source_lang="Spanish", target_lang="English"
        )

    @pytest.mark.asyncio
    @patch("routers.translation.translate")
    async def test_safe_translate_with_orig(self, mock_translate):
        """Test safe_translate with orig field"""
        mock_translate.return_value = "Translated text"

        entry = {"orig": "Original text", "other_field": "value"}
        result = await safe_translate(entry, "Spanish", "English")

        assert result["orig"] == "Original text"
        assert result["translated_text"] == "Translated text"
        mock_translate.assert_called_once_with(
            "Original text", source_lang="Spanish", target_lang="English"
        )

    @pytest.mark.asyncio
    @patch("routers.translation.translate")
    async def test_safe_translate_no_text(self, mock_translate):
        """Test safe_translate without text or orig field"""
        entry = {"other_field": "value"}
        result = await safe_translate(entry, "Spanish", "English")

        assert result["translated_text"] == "error"
        assert result["other_field"] == "value"
        mock_translate.assert_not_called()

    @pytest.mark.asyncio
    @patch("routers.translation.translate")
    async def test_safe_translate_exception(self, mock_translate):
        """Test safe_translate with translation exception"""
        mock_translate.side_effect = Exception("Translation failed")

        entry = {"text": "Original text"}
        result = await safe_translate(entry, "Spanish", "English")

        assert result["translated_text"] == "error"

    @pytest.mark.asyncio
    @patch("routers.translation.translate")
    async def test_safe_translate_none_result(self, mock_translate):
        """Test safe_translate when translate returns None"""
        mock_translate.return_value = None

        entry = {"text": "Original text"}
        result = await safe_translate(entry, "Spanish", "English")

        assert result["translated_text"] == "error"


class TestTranslationRouter:
    @patch("routers.translation.save_job")
    @patch("routers.translation.upload_fileobj")
    @patch("routers.translation.safe_translate")
    def test_doc_translate_success(
        self, mock_safe_translate, mock_upload, mock_save_job
    ):
        """Test successful document translation"""
        # Mock safe_translate to return translated entries
        mock_safe_translate.side_effect = lambda entry, source_lang, target_lang: {
            **entry,
            "translated_text": f"Translated: {entry.get('text', entry.get('orig', 'unknown'))}",
        }
        mock_upload.return_value = True

        docling_data = DoclingTranslationResponse(
            schema_name="test",
            version="1.0",
            name="test_doc",
            origin={},
            furniture={},
            texts=[{"text": "Hello"}],
            pictures=[],
            tables=[{"data": {"table_cells": [{"text": "Cell text"}]}}],
            key_value_items=[],
            form_items=[],
            pages={},
        )

        request_data = TranslateResponse(
            doc_id="doc123",
            docling=docling_data,
            source_lang="Spanish",
            target_lang="English",
        )

        response = client.post("/translation/", json=request_data.model_dump())

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["doc_id"] == "doc123"
        assert response_data["source_lang"] == "Spanish"
        assert response_data["target_lang"] == "English"

        # Verify job was saved
        assert mock_save_job.call_count == 2  # Once for processing, once for completed

    @patch("routers.translation.save_job")
    @patch("routers.translation.load_job")
    def test_get_status_success(self, mock_load_job, mock_save_job):
        """Test successful status retrieval"""
        mock_load_job.return_value = {"status": "completed"}

        response = client.get("/translation/status/doc123")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "completed"

    @patch("routers.translation.load_job")
    def test_get_status_not_found(self, mock_load_job):
        """Test status retrieval for non-existent job"""
        mock_load_job.return_value = None

        response = client.get("/translation/status/doc123")

        assert response.status_code == 404
        response_data = response.json()
        assert response_data["status"] == "failed"

    @patch("routers.translation.load_job")
    def test_get_status_processing(self, mock_load_job):
        """Test status retrieval for processing job"""
        mock_load_job.return_value = {"status": "processing"}

        response = client.get("/translation/status/doc123")

        assert response.status_code == 202
        response_data = response.json()
        assert response_data["status"] == "processing"

    @patch("routers.translation.save_job")
    @patch("routers.translation.upload_fileobj")
    def test_doc_translate_upload_failure(self, mock_upload, mock_save_job):
        """Test document translation with S3 upload failure"""
        mock_upload.return_value = False

        docling_data = DoclingTranslationResponse(
            schema_name="test",
            version="1.0",
            name="test_doc",
            origin={},
            furniture={},
            texts=[],
            pictures=[],
            tables=[],
            key_value_items=[],
            form_items=[],
            pages={},
        )

        request_data = TranslateResponse(
            doc_id="doc123",
            docling=docling_data,
            source_lang="Spanish",
            target_lang="English",
        )

        response = client.post("/translation/", json=request_data.model_dump())

        assert response.status_code == 500
        response_data = response.json()
        assert "error" in response_data

    def test_doc_translate_invalid_request(self):
        """Test document translation with invalid request data"""
        invalid_data = {
            "doc_id": "doc123"
            # Missing required fields
        }

        response = client.post("/translation/", json=invalid_data)

        assert response.status_code == 422  # Validation error
