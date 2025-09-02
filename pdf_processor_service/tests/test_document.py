from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from routers.document import router
from botocore.exceptions import ClientError
import io


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestDocumentRouter:
    @patch('routers.document.generate_external_doc_url')
    @patch('routers.document.upload_fileobj')
    @patch('routers.document.get_doc_list_append_function')
    def test_upload_document_success(self, mock_get_append, mock_upload, mock_generate_url):
        """Test successful document upload"""
        # Mock dependencies
        mock_append_func = MagicMock()
        mock_get_append.return_value = mock_append_func
        mock_upload.return_value = True
        mock_generate_url.return_value = "https://example.com/doc/doc123"
        
        # Create mock PDF file
        pdf_content = b"%PDF-1.4\n%fake pdf content"
        files = {
            "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
        }
        
        response = client.post("/documents/", files=files)
        
        assert response.status_code == 201
        response_data = response.json()
        assert "doc_id" in response_data
        assert response_data["filename"].endswith("/original.pdf")
        assert response_data["download_url"] == "https://example.com/doc/doc123"
        
        # Verify upload was called
        mock_upload.assert_called_once()
        # Verify document was added to session
        mock_append_func.assert_called_once()

    @patch('routers.document.get_doc_list_append_function')
    def test_upload_document_invalid_extension(self, mock_get_append):
        """Test document upload with invalid file extension"""
        mock_append_func = MagicMock()
        mock_get_append.return_value = mock_append_func
        
        # Create mock non-PDF file
        content = b"not a pdf file"
        files = {
            "file": ("test.txt", io.BytesIO(content), "text/plain")
        }
        
        response = client.post("/documents/", files=files)
        
        assert response.status_code == 400
        response_data = response.json()
        assert "File extension must be .pdf" in response_data["detail"]

    @patch('routers.document.get_doc_list_append_function')
    def test_upload_document_invalid_pdf_header(self, mock_get_append):
        """Test document upload with invalid PDF header"""
        mock_append_func = MagicMock()
        mock_get_append.return_value = mock_append_func
        
        # Create mock file with PDF extension but invalid header
        content = b"NOT%PDF-1.4\n%fake content"
        files = {
            "file": ("test.pdf", io.BytesIO(content), "application/pdf")
        }
        
        response = client.post("/documents/", files=files)
        
        assert response.status_code == 400
        response_data = response.json()
        assert "not a valid PDF" in response_data["detail"]

    @patch('routers.document.upload_fileobj')
    @patch('routers.document.get_doc_list_append_function')
    def test_upload_document_s3_failure(self, mock_get_append, mock_upload):
        """Test document upload with S3 upload failure"""
        mock_append_func = MagicMock()
        mock_get_append.return_value = mock_append_func
        mock_upload.return_value = False
        
        # Create mock PDF file
        pdf_content = b"%PDF-1.4\n%fake pdf content"
        files = {
            "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
        }
        
        response = client.post("/documents/", files=files)
        
        assert response.status_code == 500
        response_data = response.json()
        assert "Failed to upload file to S3" in response_data["detail"]

    @patch('routers.document.upload_fileobj')
    @patch('routers.document.get_doc_list_append_function')
    def test_upload_document_unexpected_error(self, mock_get_append, mock_upload):
        """Test document upload with unexpected error"""
        mock_append_func = MagicMock()
        mock_get_append.return_value = mock_append_func
        mock_upload.side_effect = Exception("Unexpected error")
        
        # Create mock PDF file
        pdf_content = b"%PDF-1.4\n%fake pdf content"
        files = {
            "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
        }
        
        response = client.post("/documents/", files=files)
        
        assert response.status_code == 500
        response_data = response.json()
        assert "Internal server error" in response_data["detail"]

    @patch('routers.document.get_object_stream')
    @patch('routers.document.validate_session_doc_pair')
    def test_get_document_success(self, mock_validate, mock_get_stream):
        """Test successful document retrieval"""
        mock_validate.return_value = True
        mock_stream = io.BytesIO(b"%PDF-1.4\n%fake pdf content")
        mock_get_stream.return_value = mock_stream
        
        response = client.get("/documents/doc123")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        mock_get_stream.assert_called_once_with("doc123/original.pdf")

    @patch('routers.document.get_object_stream')
    @patch('routers.document.validate_session_doc_pair')
    def test_get_document_not_found(self, mock_validate, mock_get_stream):
        """Test document retrieval when document not found"""
        mock_validate.return_value = True
        
        # Mock ClientError for NoSuchKey
        error_response = {
            "Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}
        }
        mock_get_stream.side_effect = ClientError(error_response, "GetObject")
        
        response = client.get("/documents/doc123")
        
        assert response.status_code == 404
        response_data = response.json()
        assert "Document not found" in response_data["detail"]

    @patch('routers.document.get_object_stream')
    @patch('routers.document.validate_session_doc_pair')
    def test_get_document_s3_error(self, mock_validate, mock_get_stream):
        """Test document retrieval with S3 error"""
        mock_validate.return_value = True
        
        # Mock ClientError for other S3 errors
        error_response = {
            "Error": {"Code": "AccessDenied", "Message": "Access denied"}
        }
        mock_get_stream.side_effect = ClientError(error_response, "GetObject")
        
        response = client.get("/documents/doc123")
        
        assert response.status_code == 500
        response_data = response.json()
        assert "Failed to check document" in response_data["detail"]

    @patch('routers.document.delete_file')
    @patch('routers.document.validate_session_doc_pair')
    @patch('routers.document.get_doc_list_remove_function')
    def test_delete_document_success(self, mock_get_remove, mock_validate, mock_delete):
        """Test successful document deletion"""
        mock_validate.return_value = True
        mock_remove_func = MagicMock()
        mock_get_remove.return_value = mock_remove_func
        mock_delete.return_value = True
        
        response = client.delete("/documents/doc123")
        
        assert response.status_code == 204
        mock_delete.assert_called_once_with("doc123/original.pdf")
        mock_remove_func.assert_called_once_with("doc123")

    @patch('routers.document.delete_file')
    @patch('routers.document.validate_session_doc_pair')
    @patch('routers.document.get_doc_list_remove_function')
    def test_delete_document_not_found(self, mock_get_remove, mock_validate, mock_delete):
        """Test document deletion when document not found"""
        mock_validate.return_value = True
        mock_remove_func = MagicMock()
        mock_get_remove.return_value = mock_remove_func
        mock_delete.return_value = False
        
        response = client.delete("/documents/doc123")
        
        assert response.status_code == 404
        response_data = response.json()
        assert "Document not found" in response_data["detail"]
        
        # Verify remove function was not called since deletion failed
        mock_remove_func.assert_not_called()

    def test_upload_document_missing_file(self):
        """Test document upload without file"""
        response = client.post("/documents/")
        
        assert response.status_code == 422  # Validation error

    @patch('routers.document.get_doc_list_append_function')
    def test_upload_document_empty_file(self, mock_get_append):
        """Test document upload with empty file"""
        mock_append_func = MagicMock()
        mock_get_append.return_value = mock_append_func
        
        # Create empty file with PDF extension
        files = {
            "file": ("empty.pdf", io.BytesIO(b""), "application/pdf")
        }
        
        response = client.post("/documents/", files=files)
        
        assert response.status_code == 400
        response_data = response.json()
        assert "not a valid PDF" in response_data["detail"]
