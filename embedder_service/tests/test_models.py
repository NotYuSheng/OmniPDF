import pytest
from pydantic import ValidationError
from models.embed import ProcessingConfig, DataRequest


class TestProcessingConfig:
    def test_default_processing_config(self):
        """Test ProcessingConfig with default values"""
        config = ProcessingConfig()

        assert config.chunk_size == 512
        assert config.overlap == 50
        assert config.embedding_model == "all-MiniLM-L6-v2"
        assert config.breakpoint_threshold_amount == 90.0
        assert config.min_chunk_size == 100
        assert config.max_chunk_size == 1000
        assert config.store_in_chroma is True

    def test_custom_processing_config(self):
        """Test ProcessingConfig with custom values"""
        config = ProcessingConfig(
            chunk_size=256,
            overlap=25,
            embedding_model="custom-model",
            min_chunk_size=50,
            max_chunk_size=2000,
            store_in_chroma=False,
        )

        assert config.chunk_size == 256
        assert config.overlap == 25
        assert config.embedding_model == "custom-model"
        assert config.min_chunk_size == 50
        assert config.max_chunk_size == 2000
        assert config.store_in_chroma is False

    def test_processing_config_field_validation(self):
        """Test ProcessingConfig field validation"""
        # Test negative chunk size
        with pytest.raises(ValidationError):
            ProcessingConfig(chunk_size=-1)

        # Test negative overlap
        with pytest.raises(ValidationError):
            ProcessingConfig(overlap=-1)

    def test_processing_config_chunk_size_constraints(self):
        """Test ProcessingConfig chunk size logical constraints"""
        config = ProcessingConfig(
            min_chunk_size=200,
            max_chunk_size=100,  # max < min
        )

        # The model should allow this even though it's illogical
        # Business logic validation should happen elsewhere
        assert config.min_chunk_size == 200
        assert config.max_chunk_size == 100


class TestDataRequest:
    def test_valid_data_request(self):
        """Test creation of valid DataRequest"""
        config = ProcessingConfig()
        request = DataRequest(
            doc_id="test_doc_123",
            session_id="session_456",
            text="This is sample text to be processed",
            config=config,
            pages_info=[],
        )

        assert request.doc_id == "test_doc_123"
        assert request.session_id == "session_456"
        assert request.text == "This is sample text to be processed"
        assert isinstance(request.config, ProcessingConfig)
        assert request.pages_info == []

    def test_data_request_with_pages_info(self):
        """Test DataRequest with pages information"""
        config = ProcessingConfig()
        pages_info = [
            {"page": 1, "start_char": 0, "end_char": 100},
            {"page": 2, "start_char": 100, "end_char": 200},
        ]

        request = DataRequest(
            doc_id="test_doc",
            session_id="session_123",
            text="Sample text",
            config=config,
            pages_info=pages_info,
        )

        assert len(request.pages_info) == 2
        assert request.pages_info[0]["page"] == 1
        assert request.pages_info[1]["page"] == 2

    def test_data_request_empty_text(self):
        """Test DataRequest with empty text"""
        config = ProcessingConfig()
        request = DataRequest(
            doc_id="test_doc",
            session_id="session_123",
            text="",  # Empty text should be allowed at model level
            config=config,
            pages_info=[],
        )

        assert request.text == ""

    def test_invalid_data_request_missing_required(self):
        """Test DataRequest validation with missing required fields"""
        with pytest.raises(ValidationError):
            DataRequest()  # Missing all required fields

    def test_invalid_data_request_missing_doc_id(self):
        """Test DataRequest validation without doc_id"""
        config = ProcessingConfig()
        with pytest.raises(ValidationError):
            DataRequest(
                session_id="session_123",
                text="Sample text",
                config=config,
                pages_info=[],
            )

    def test_invalid_data_request_missing_session_id(self):
        """Test DataRequest validation without session_id"""
        config = ProcessingConfig()
        with pytest.raises(ValidationError):
            DataRequest(
                doc_id="test_doc", text="Sample text", config=config, pages_info=[]
            )

    def test_invalid_data_request_missing_config(self):
        """Test DataRequest validation without config"""
        with pytest.raises(ValidationError):
            DataRequest(
                doc_id="test_doc",
                session_id="session_123",
                text="Sample text",
                pages_info=[],
            )

    def test_data_request_config_nested_validation(self):
        """Test DataRequest with invalid nested config"""
        with pytest.raises(ValidationError):
            DataRequest(
                doc_id="test_doc",
                session_id="session_123",
                text="Sample text",
                config="invalid_config",  # Should be ProcessingConfig object
                pages_info=[],
            )
