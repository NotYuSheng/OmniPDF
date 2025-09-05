import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.bypass import router, s3_upload
import io


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestS3UploadFunction:
    @patch("routers.bypass.generate_presigned_url")
    @patch("routers.bypass.upload_fileobj")
    def test_s3_upload_success(self, mock_upload, mock_generate_url):
        """Test successful S3 upload"""
        mock_upload.return_value = True
        mock_generate_url.return_value = "https://example.com/presigned-url"

        file_bytes = b"mock json content"
        key = "doc123/original.json"

        result = s3_upload(file_bytes, key)

        assert result == "https://example.com/presigned-url"
        mock_upload.assert_called_once()
        mock_generate_url.assert_called_once_with(key)

    @patch("routers.bypass.upload_fileobj")
    def test_s3_upload_failure(self, mock_upload):
        """Test S3 upload failure"""
        mock_upload.return_value = False

        file_bytes = b"mock json content"
        key = "doc123/original.json"

        with pytest.raises(RuntimeError, match="S3 upload returned False"):
            s3_upload(file_bytes, key)


class TestBypassRouter:
    @patch("routers.bypass.run_in_threadpool")
    def test_dump_files_success_original(self, mock_run_in_threadpool):
        """Test successful file dump with original JSON"""
        mock_run_in_threadpool.return_value = "https://example.com/presigned-url"

        # Create mock file
        json_content = b'{"test": "data"}'
        files = {
            "json_file": ("test.json", io.BytesIO(json_content), "application/json")
        }

        response = client.post("/bypass/doc123?json_name=original", files=files)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["doc_id"] == "doc123"
        assert response_data["filename"] == "doc123/original.json"
        assert response_data["download_url"] == "https://example.com/presigned-url"

        mock_run_in_threadpool.assert_called_once()

    @patch("routers.bypass.run_in_threadpool")
    def test_dump_files_success_translated(self, mock_run_in_threadpool):
        """Test successful file dump with translated JSON"""
        mock_run_in_threadpool.return_value = "https://example.com/presigned-url"

        # Create mock file
        json_content = b'{"test": "translated data"}'
        files = {
            "json_file": ("test.json", io.BytesIO(json_content), "application/json")
        }

        response = client.post("/bypass/doc123?json_name=translated", files=files)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["doc_id"] == "doc123"
        assert response_data["filename"] == "doc123/translated.json"
        assert response_data["download_url"] == "https://example.com/presigned-url"

    @patch("routers.bypass.run_in_threadpool")
    def test_dump_files_upload_failure(self, mock_run_in_threadpool):
        """Test file dump with upload failure"""
        mock_run_in_threadpool.side_effect = RuntimeError("S3 upload failed")

        # Create mock file
        json_content = b'{"test": "data"}'
        files = {
            "json_file": ("test.json", io.BytesIO(json_content), "application/json")
        }

        response = client.post("/bypass/doc123?json_name=original", files=files)

        assert response.status_code == 500
        response_data = response.json()
        assert "Upload failed due to an internal error" in response_data["detail"]

    @patch("routers.bypass.run_in_threadpool")
    def test_dump_files_generic_exception(self, mock_run_in_threadpool):
        """Test file dump with generic exception"""
        mock_run_in_threadpool.side_effect = Exception("Unexpected error")

        # Create mock file
        json_content = b'{"test": "data"}'
        files = {
            "json_file": ("test.json", io.BytesIO(json_content), "application/json")
        }

        response = client.post("/bypass/doc123?json_name=original", files=files)

        assert response.status_code == 500
        response_data = response.json()
        assert "Upload failed due to an internal error" in response_data["detail"]

    def test_dump_files_invalid_json_name(self):
        """Test file dump with invalid json_name parameter"""
        # Create mock file
        json_content = b'{"test": "data"}'
        files = {
            "json_file": ("test.json", io.BytesIO(json_content), "application/json")
        }

        response = client.post("/bypass/doc123?json_name=invalid", files=files)

        assert response.status_code == 422  # Validation error for invalid literal

    def test_dump_files_missing_file(self):
        """Test file dump without file upload"""
        response = client.post("/bypass/doc123?json_name=original")

        assert response.status_code == 422  # Validation error for missing file

    def test_dump_files_missing_json_name(self):
        """Test file dump without json_name parameter"""
        # Create mock file
        json_content = b'{"test": "data"}'
        files = {
            "json_file": ("test.json", io.BytesIO(json_content), "application/json")
        }

        response = client.post("/bypass/doc123", files=files)

        assert response.status_code == 422  # Validation error for missing parameter

    def test_dump_files_empty_file(self):
        """Test file dump with empty file"""
        # Create empty file
        files = {"json_file": ("test.json", io.BytesIO(b""), "application/json")}

        with patch("routers.bypass.run_in_threadpool") as mock_run_in_threadpool:
            mock_run_in_threadpool.return_value = "https://example.com/presigned-url"

            response = client.post("/bypass/doc123?json_name=original", files=files)

            assert response.status_code == 200
            # Should still work with empty file
            mock_run_in_threadpool.assert_called_once()
