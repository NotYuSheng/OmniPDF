import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from routers.render import router, redact_and_render, handle_file
from models.render import AnnotationResponse, DoclingTranslationResponse
from botocore.exceptions import ClientError


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestRedactAndRenderFunction:
    @patch("routers.render.pymupdf.open")
    def test_redact_and_render_success(self, mock_pymupdf_open):
        """Test successful PDF redaction and rendering"""
        # Mock PDF document and pages
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.rect = [0, 0, 100, 100]
        mock_page.add_redact_annot = MagicMock()
        mock_page.apply_redactions = MagicMock()
        mock_page.clean_contents = MagicMock()
        mock_page.insert_htmlbox = MagicMock()

        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.subset_fonts = MagicMock()
        mock_doc.save = MagicMock()

        mock_pymupdf_open.return_value = mock_doc

        pdf_bytes = b"mock pdf content"
        annotations = {
            "docling": {
                "texts": [
                    {
                        "translated_text": "Translated text",
                        "prov": [
                            {"page_no": 1, "bbox": {"l": 10, "t": 20, "r": 50, "b": 40}}
                        ],
                    }
                ]
            }
        }

        result = redact_and_render(pdf_bytes, annotations)

        assert isinstance(result, bytes)
        mock_pymupdf_open.assert_called_once()
        mock_page.add_redact_annot.assert_called_once()
        mock_page.apply_redactions.assert_called_once()
        mock_page.insert_htmlbox.assert_called_once()

    @patch("routers.render.pymupdf.open")
    def test_redact_and_render_no_annotations(self, mock_pymupdf_open):
        """Test PDF rendering with no annotations"""
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.rect = [0, 0, 100, 100]

        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.subset_fonts = MagicMock()
        mock_doc.save = MagicMock()

        mock_pymupdf_open.return_value = mock_doc

        pdf_bytes = b"mock pdf content"
        annotations = {"docling": {"texts": []}}

        result = redact_and_render(pdf_bytes, annotations)

        assert isinstance(result, bytes)
        mock_pymupdf_open.assert_called_once()

    @patch("routers.render.pymupdf.open")
    def test_redact_and_render_insert_error(self, mock_pymupdf_open):
        """Test PDF rendering with insert error"""
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.rect = [0, 0, 100, 100]
        mock_page.insert_htmlbox.side_effect = Exception("Insert failed")

        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.__getitem__.return_value = mock_page

        mock_pymupdf_open.return_value = mock_doc

        pdf_bytes = b"mock pdf content"
        annotations = {
            "docling": {
                "texts": [
                    {
                        "translated_text": "Translated text",
                        "prov": [
                            {"page_no": 1, "bbox": {"l": 10, "t": 20, "r": 50, "b": 40}}
                        ],
                    }
                ]
            }
        }

        with pytest.raises(Exception, match="Insert failed"):
            redact_and_render(pdf_bytes, annotations)

    @patch("routers.render.pymupdf.open")
    def test_redact_and_render_non_string_text(self, mock_pymupdf_open):
        """Test PDF rendering with non-string translated text"""
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.rect = [0, 0, 100, 100]
        mock_page.insert_htmlbox = MagicMock()

        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.subset_fonts = MagicMock()
        mock_doc.save = MagicMock()

        mock_pymupdf_open.return_value = mock_doc

        pdf_bytes = b"mock pdf content"
        annotations = {
            "docling": {
                "texts": [
                    {
                        "translated_text": 123,  # Non-string text (integer)
                        "prov": [
                            {"page_no": 1, "bbox": {"l": 10, "t": 20, "r": 50, "b": 40}}
                        ],
                    }
                ]
            }
        }

        result = redact_and_render(pdf_bytes, annotations)

        assert isinstance(result, bytes)
        # Should insert "Error" for non-string text
        mock_page.insert_htmlbox.assert_called_with((10, 80, 50, 60), "Error")


class TestHandleFileFunction:
    @patch("routers.render.generate_presigned_url")
    @patch("routers.render.upload_fileobj")
    def test_handle_file_success(self, mock_upload, mock_generate_url):
        """Test successful file handling"""
        mock_upload.return_value = True
        mock_generate_url.return_value = "https://example.com/presigned-url"

        buffer_bytes = b"mock file content"
        key = "doc123/rendered.pdf"

        result = handle_file(buffer_bytes, key)

        assert result == "https://example.com/presigned-url"
        mock_upload.assert_called_once()
        mock_generate_url.assert_called_once_with(key)

    @patch("routers.render.upload_fileobj")
    def test_handle_file_upload_failure(self, mock_upload):
        """Test file handling with upload failure"""
        mock_upload.return_value = False

        buffer_bytes = b"mock file content"
        key = "doc123/rendered.pdf"

        with pytest.raises(RuntimeError, match="Failed to upload file to S3"):
            handle_file(buffer_bytes, key)


class TestPdfRenderRouter:
    @patch("routers.render.run_in_threadpool")
    @patch("routers.render.httpx.AsyncClient")
    def test_pdf_render_success(self, mock_httpx_client, mock_run_in_threadpool):
        """Test successful PDF rendering"""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = b"mock pdf content"
        mock_response.headers = {"Content-Length": "1000"}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

        # Mock threadpool operations
        mock_run_in_threadpool.side_effect = [
            b"rendered pdf content",  # redact_and_render result
            "https://example.com/presigned-url",  # handle_file result
        ]

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

        annotation_data = AnnotationResponse(
            doc_id="doc123",
            docling=docling_data,
            source_lang="Spanish",
            target_lang="English",
        )

        response = client.post(
            "/render/doc123?doc_url=https://example.com/document.pdf",
            json=annotation_data.model_dump(),
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "doc_id" in response_data
        assert "filename" in response_data
        assert "download_url" in response_data

    @patch("routers.render.httpx.AsyncClient")
    def test_pdf_render_http_error(self, mock_httpx_client):
        """Test PDF rendering with HTTP error"""
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not found", request=MagicMock(), response=MagicMock(status_code=404)
            )
        )
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

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

        annotation_data = AnnotationResponse(
            doc_id="doc123",
            docling=docling_data,
            source_lang="Spanish",
            target_lang="English",
        )

        response = client.post(
            "/render/doc123?doc_url=https://example.com/document.pdf",
            json=annotation_data.model_dump(),
        )

        assert (
            response.status_code == 422
        )  # HTTPStatusError gets raised before our handler

    @patch("routers.render.run_in_threadpool")
    @patch("routers.render.httpx.AsyncClient")
    def test_pdf_render_processing_error(
        self, mock_httpx_client, mock_run_in_threadpool
    ):
        """Test PDF rendering with processing error"""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = b"mock pdf content"
        mock_response.headers = {"Content-Length": "1000"}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

        # Mock rendering failure
        mock_run_in_threadpool.side_effect = Exception("Rendering failed")

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

        annotation_data = AnnotationResponse(
            doc_id="doc123",
            docling=docling_data,
            source_lang="Spanish",
            target_lang="English",
        )

        response = client.post(
            "/render/doc123?doc_url=https://example.com/document.pdf",
            json=annotation_data.model_dump(),
        )

        assert response.status_code == 500
        response_data = response.json()
        assert "PDF processing error" in response_data["detail"]

    @patch("routers.render.run_in_threadpool")
    @patch("routers.render.httpx.AsyncClient")
    def test_pdf_render_s3_client_error(
        self, mock_httpx_client, mock_run_in_threadpool
    ):
        """Test PDF rendering with S3 client error"""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = b"mock pdf content"
        mock_response.headers = {"Content-Length": "1000"}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

        # Mock successful rendering but S3 client error
        client_error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "PutObject"
        )
        mock_run_in_threadpool.side_effect = [
            b"rendered pdf content",  # redact_and_render result
            client_error,  # handle_file result
        ]

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

        annotation_data = AnnotationResponse(
            doc_id="doc123",
            docling=docling_data,
            source_lang="Spanish",
            target_lang="English",
        )

        response = client.post(
            "/render/doc123?doc_url=https://example.com/document.pdf",
            json=annotation_data.model_dump(),
        )

        assert response.status_code == 502
        response_data = response.json()
        assert "S3 service error" in response_data["detail"]

    def test_pdf_render_invalid_request(self):
        """Test PDF rendering with invalid request data"""
        invalid_data = {
            "doc_id": "doc123"
            # Missing required fields
        }

        response = client.post(
            "/render/doc123?doc_url=https://example.com/document.pdf", json=invalid_data
        )

        assert response.status_code == 422  # Validation error
