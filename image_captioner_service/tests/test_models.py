import pytest
from pydantic import ValidationError
from models.caption import ImageCaptioningRequest, ImageCaptioningResponse
from models.vlm_config import VLMConfig, PromptTemplates, CaptionOptimizer


class TestImageCaptioningRequest:
    def test_valid_image_captioning_request(self):
        """Test creation of valid ImageCaptioningRequest"""
        request = ImageCaptioningRequest(
            doc_id="doc123",
            image_id="img456",
            image_url="https://example.com/image.png",
            prompt="Describe this image in detail",
        )

        assert request.doc_id == "doc123"
        assert request.image_id == "img456"
        assert request.image_url == "https://example.com/image.png"
        assert request.prompt == "Describe this image in detail"

    def test_image_captioning_request_default_prompt(self):
        """Test ImageCaptioningRequest with default prompt"""
        request = ImageCaptioningRequest(
            doc_id="doc123",
            image_id="img456",
            image_url="https://example.com/image.png",
        )

        assert request.prompt == "Generate a descriptive caption for this image."

    def test_invalid_image_captioning_request_missing_doc_id(self):
        """Test ImageCaptioningRequest validation without doc_id"""
        with pytest.raises(ValidationError):
            ImageCaptioningRequest(
                image_id="img456", image_url="https://example.com/image.png"
            )

    def test_invalid_image_captioning_request_missing_image_id(self):
        """Test ImageCaptioningRequest validation without image_id"""
        with pytest.raises(ValidationError):
            ImageCaptioningRequest(
                doc_id="doc123", image_url="https://example.com/image.png"
            )

    def test_invalid_image_captioning_request_missing_image_url(self):
        """Test ImageCaptioningRequest validation without image_url"""
        with pytest.raises(ValidationError):
            ImageCaptioningRequest(doc_id="doc123", image_id="img456")

    def test_image_captioning_request_empty_strings(self):
        """Test ImageCaptioningRequest with empty string values"""
        with pytest.raises(ValidationError):
            ImageCaptioningRequest(
                doc_id="", image_id="img456", image_url="https://example.com/image.png"
            )


class TestImageCaptioningResponse:
    def test_valid_image_captioning_response(self):
        """Test creation of valid ImageCaptioningResponse"""
        response = ImageCaptioningResponse(
            caption="A beautiful sunset over the ocean with waves crashing on the shore."
        )

        assert (
            response.caption
            == "A beautiful sunset over the ocean with waves crashing on the shore."
        )

    def test_image_captioning_response_empty_caption(self):
        """Test ImageCaptioningResponse with empty caption"""
        response = ImageCaptioningResponse(caption="")

        assert response.caption == ""

    def test_invalid_image_captioning_response_missing_caption(self):
        """Test ImageCaptioningResponse validation without caption"""
        with pytest.raises(ValidationError):
            ImageCaptioningResponse()


class TestVLMConfig:
    def test_vlm_config_initialization_with_env(self):
        """Test VLMConfig initialization with environment variables"""

        # Mock environment variables
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("OPENAI_VLM", "gpt-4-vision")
            mp.setenv("MODEL_TEMPERATURE", "0.2")
            mp.setenv("MODEL_MAX_TOKENS", "1000")
            mp.setenv("MODEL_TOP_P", "0.8")
            mp.setenv("MODEL_FREQ_PENALTY", "0.2")
            mp.setenv("MODEL_PRESENCE_PENALTY", "0.2")
            mp.setenv("ENABLE_RESPONSE_POST_PROCESSING", "false")

            config = VLMConfig()

            assert config.model_name == "gpt-4-vision"
            assert config.generation_params["temperature"] == 0.2
            assert config.generation_params["max_tokens"] == 1000
            assert config.generation_params["top_p"] == 0.8
            assert config.generation_params["frequency_penalty"] == 0.2
            assert config.generation_params["presence_penalty"] == 0.2
            assert config.enable_response_post_processing is False

    def test_vlm_config_default_values(self):
        """Test VLMConfig with default values when env vars not set"""

        # Mock only required environment variable
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("OPENAI_VLM", "gpt-4-vision")
            # Remove all optional env vars to test defaults
            for key in [
                "MODEL_TEMPERATURE",
                "MODEL_MAX_TOKENS",
                "MODEL_TOP_P",
                "MODEL_FREQ_PENALTY",
                "MODEL_PRESENCE_PENALTY",
                "ENABLE_RESPONSE_POST_PROCESSING",
            ]:
                mp.delenv(key, raising=False)

            config = VLMConfig()

            assert config.model_name == "gpt-4-vision"
            assert config.generation_params["temperature"] == 0.1
            assert config.generation_params["max_tokens"] == 500
            assert config.generation_params["top_p"] == 0.9
            assert config.generation_params["frequency_penalty"] == 0.1
            assert config.generation_params["presence_penalty"] == 0.1
            assert config.enable_response_post_processing is True

    def test_vlm_config_missing_required_env(self):
        """Test VLMConfig raises error when required env var is missing"""

        with pytest.MonkeyPatch().context() as mp:
            mp.delenv("OPENAI_VLM", raising=False)

            with pytest.raises(KeyError):
                VLMConfig()


class TestPromptTemplates:
    def test_get_system_prompt(self):
        """Test get_system_prompt returns a string"""
        prompt = PromptTemplates.get_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "You are a highly specialized AI assistant" in prompt
        assert "Core Directives:" in prompt
        assert "Content-Specific Instructions:" in prompt


class TestCaptionOptimizer:
    def test_post_process_llm_response_basic(self):
        """Test basic post-processing of LLM response"""
        response = "This is a test caption"
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == "This is a test caption."

    def test_post_process_llm_response_already_ends_with_period(self):
        """Test post-processing when response already ends with period"""
        response = "This is a test caption."
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == "This is a test caption."

    def test_post_process_llm_response_ends_with_punctuation(self):
        """Test post-processing when response ends with other punctuation"""
        response = "Is this a test caption?"
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == "Is this a test caption?"

    def test_post_process_llm_response_ends_with_exclamation(self):
        """Test post-processing when response ends with exclamation"""
        response = "What a great image!"
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == "What a great image!"

    def test_post_process_llm_response_ends_with_colon(self):
        """Test post-processing when response ends with colon"""
        response = "The image shows:"
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == "The image shows:"

    def test_post_process_llm_response_remove_duplicate_lines(self):
        """Test post-processing removes consecutive duplicate lines"""
        response = "Line 1\nLine 2\nLine 2\nLine 3"
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == "Line 1\nLine 2\nLine 3."

    def test_post_process_llm_response_keep_non_consecutive_duplicates(self):
        """Test post-processing keeps non-consecutive duplicate lines"""
        response = "Line 1\nLine 2\nLine 3\nLine 2"
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == "Line 1\nLine 2\nLine 3\nLine 2."

    def test_post_process_llm_response_empty_string(self):
        """Test post-processing with empty string"""
        response = ""
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == ""

    def test_post_process_llm_response_whitespace_only(self):
        """Test post-processing with whitespace only"""
        response = "   \n   \n   "
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == ""

    def test_post_process_llm_response_with_trailing_whitespace(self):
        """Test post-processing with trailing whitespace"""
        response = "This is a test caption   "
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == "This is a test caption."

    def test_post_process_llm_response_multiline_with_ending(self):
        """Test post-processing multiline response"""
        response = "Line 1\nLine 2\nFinal line"
        processed = CaptionOptimizer.post_process_llm_response(response)

        assert processed == "Line 1\nLine 2\nFinal line."
