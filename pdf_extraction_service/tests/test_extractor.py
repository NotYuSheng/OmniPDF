import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from routers.extractor import process_pdf


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_docling_data():
    return {
        'schema_name': 'docling',
        'version': '1.0',
        'name': 'test.pdf',
        'origin': {'filename': 'test.pdf'},
        'furniture': {},
        'texts': [{'content': 'Sample text'}],
        'pictures': [{'image': {'uri': 'test_uri'}}],
        'tables': [],
        'key_value_items': [],
        'form_items': [],
        'pages': {
            '0': {'image': {'uri': 'page_uri'}}
        },
        'body': 'removed',
        'groups': 'removed'
    }


@pytest.fixture
def mock_picture_item():
    mock_item = MagicMock()
    mock_image = MagicMock()
    mock_item.get_image.return_value = mock_image
    return mock_item


class TestProcessPdf:
    @patch('routers.extractor.DocumentConverter')
    @patch('routers.extractor.upload_fileobj')
    @patch('routers.extractor.save_job')
    @patch('routers.extractor.redis_image_sets')
    def test_successful_pdf_processing(self, mock_redis, mock_save_job, 
                                     mock_upload, mock_converter_class, 
                                     sample_docling_data, mock_picture_item):
        """Test successful PDF processing"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter
        
        mock_result = MagicMock()
        mock_result.document.export_to_dict.return_value = sample_docling_data
        mock_result.document.iterate_items.return_value = [
            (mock_picture_item, None)
        ]
        mock_converter.convert.return_value = mock_result
        
        mock_upload.return_value = True
        
        # Execute
        process_pdf("test_doc", "http://test.com/pdf", 2.0)
        
        # Verify
        mock_converter_class.assert_called_once()
        mock_converter.convert.assert_called_once_with("http://test.com/pdf")
        
        # Verify JSON upload (image upload skipped since mock doesn't pass isinstance check)
        assert mock_upload.call_count == 1  # Just JSON
        
        # Verify job save
        mock_save_job.assert_called_once()
        args = mock_save_job.call_args
        assert args[1]['doc_id'] == "test_doc"
        assert args[1]['status'] == "completed"

    @patch('routers.extractor.DocumentConverter')
    @patch('routers.extractor.save_job')
    def test_pdf_processing_failure(self, mock_save_job, mock_converter_class):
        """Test PDF processing failure handling"""
        mock_converter_class.side_effect = Exception("Conversion failed")
        
        process_pdf("test_doc", "http://test.com/pdf")
        
        # Verify error job is saved
        mock_save_job.assert_called_once()
        args = mock_save_job.call_args
        assert args[1]['doc_id'] == "test_doc"
        assert args[1]['status'] == "failed"
        assert "Failed to download or parse document" in args[1]['job_data']['message']

    @patch('routers.extractor.upload_fileobj')
    @patch('routers.extractor.DocumentConverter')
    @patch('routers.extractor.save_job')
    def test_s3_upload_failure(self, mock_save_job, mock_converter_class, 
                              mock_upload, sample_docling_data):
        """Test handling of S3 upload failure"""
        # Setup converter success but S3 failure
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter
        mock_result = MagicMock()
        mock_result.document.export_to_dict.return_value = sample_docling_data
        mock_result.document.iterate_items.return_value = []
        mock_converter.convert.return_value = mock_result
        
        mock_upload.return_value = False  # Simulate S3 failure
        
        # Call the function - it should not raise but handle the error gracefully
        process_pdf("test_doc", "http://test.com/pdf")
        
        # Verify that job was saved with failed status due to upload failure
        mock_save_job.assert_called_once()
        call_args = mock_save_job.call_args
        assert call_args[1]['status'] == 'failed'
        assert call_args[1]['doc_id'] == 'test_doc'


class TestExtractorRoutes:
    def test_submit_pdf_endpoint(self, client):
        """Test PDF submission endpoint"""
        with patch('routers.extractor.save_job') as mock_save_job, \
             patch('routers.extractor.process_pdf') as mock_process:
            response = client.post(
                "/documents/extract",
                params={
                    "doc_id": "test_doc",
                    "download_url": "http://test.com/pdf"
                }
            )
            
            assert response.status_code == 202
            data = response.json()
            assert data["doc_id"] == "test_doc"
            assert data["status"] == "processing"
            
            # Should be called once immediately for "processing" status
            # Background task is mocked so won't call it again for "failed"
            mock_save_job.assert_called_once()

    def test_get_status_processing(self, client):
        """Test get status for processing document"""
        with patch('routers.extractor.load_job') as mock_load_job:
            mock_load_job.return_value = {
                "status": "processing",
                "data": {}
            }
            
            response = client.get("/documents/test_doc")
            
            assert response.status_code == 200
            data = response.json()
            assert data["doc_id"] == "test_doc"
            assert data["status"] == "processing"
            assert data["result"] is None

    def test_get_status_completed(self, client):
        """Test get status for completed document"""
        mock_result = {
            "schema_name": "docling",
            "version": "1.0", 
            "name": "test.pdf",
            "origin": {},
            "furniture": {},
            "texts": [],
            "pictures": [],
            "tables": [],
            "key_value_items": [],
            "form_items": [],
            "pages": {}
        }
        
        with patch('routers.extractor.load_job') as mock_load_job:
            mock_load_job.return_value = {
                "status": "completed",
                "data": {"result": mock_result}
            }
            
            response = client.get("/documents/test_doc")
            
            assert response.status_code == 200
            data = response.json()
            assert data["doc_id"] == "test_doc"
            assert data["status"] == "completed"
            assert data["result"] is not None
            assert data["result"]["schema_name"] == "docling"

    def test_get_status_not_found(self, client):
        """Test get status for non-existent document"""
        with patch('routers.extractor.load_job') as mock_load_job:
            mock_load_job.return_value = None
            
            response = client.get("/documents/nonexistent")
            
            assert response.status_code == 404

    def test_get_status_failed(self, client):
        """Test get status for failed document processing"""
        with patch('routers.extractor.load_job') as mock_load_job:
            mock_load_job.return_value = {
                "status": "failed",
                "data": {"message": "Processing failed"}
            }
            
            response = client.get("/documents/failed_doc")
            
            assert response.status_code == 500
