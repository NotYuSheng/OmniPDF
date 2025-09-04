import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from routers.caption import router, get_image
from models.caption import ImageCaptioningRequest
from PIL import Image
import io


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_dependencies():
    """Ensure dependency overrides are cleared between tests"""
    yield
    app.dependency_overrides.clear()


class TestGetImageFunction:
    @pytest.mark.asyncio
    @patch("routers.caption.http_client")
    async def test_get_image_success(self, mock_http_client):
        """Test successful image retrieval"""
        # Create a mock image
        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        mock_response = MagicMock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        image_bytes, image_format = await get_image("https://example.com/image.png")

        assert isinstance(image_bytes, bytes)
        assert image_format == "png"
        mock_http_client.get.assert_called_once_with(
            "https://example.com/image.png", follow_redirects=True
        )

    @pytest.mark.asyncio
    @patch("routers.caption.http_client")
    async def test_get_image_http_403_error(self, mock_http_client):
        """Test image retrieval with 403 HTTP error"""
        mock_response = MagicMock()
        mock_response.status_code = 403
        http_error = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=mock_response
        )

        mock_http_client.get = AsyncMock(side_effect=http_error)

        with pytest.raises(Exception) as exc_info:
            await get_image("https://example.com/image.png")

        assert "Invalid or expired S3 signed URL" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("routers.caption.http_client")
    async def test_get_image_http_500_error(self, mock_http_client):
        """Test image retrieval with 500 HTTP error"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=mock_response
        )

        mock_http_client.get = AsyncMock(side_effect=http_error)

        with pytest.raises(Exception) as exc_info:
            await get_image("https://example.com/image.png")

        assert "Failed to fetch image" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("routers.caption.http_client")
    async def test_get_image_request_error(self, mock_http_client):
        """Test image retrieval with request error"""
        mock_http_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )

        with pytest.raises(Exception) as exc_info:
            await get_image("https://example.com/image.png")

        assert "Failed to fetch image" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("routers.caption.http_client")
    async def test_get_image_invalid_image_data(self, mock_http_client):
        """Test image retrieval with invalid image data"""
        mock_response = MagicMock()
        mock_response.content = b"not an image"
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(Exception) as exc_info:
            await get_image("https://example.com/image.png")

        assert "Failed to process image" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("routers.caption.http_client")
    async def test_get_image_jpeg_format(self, mock_http_client):
        """Test image retrieval with JPEG format"""
        # Create a mock JPEG image
        img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        mock_response = MagicMock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_http_client.get = AsyncMock(return_value=mock_response)

        image_bytes, image_format = await get_image("https://example.com/image.jpg")

        assert isinstance(image_bytes, bytes)
        assert image_format == "jpeg"


class TestCaptionRouter:
    @patch("routers.caption.get_image")
    def test_generate_image_caption_success(self, mock_get_image):
        """Test successful image caption generation"""
        from shared_utils.openai_client import get_openai_client

        # Mock image retrieval as async
        async def mock_get_image_func(*args, **kwargs):
            return (b"mock_image_bytes", "png")

        mock_get_image.side_effect = mock_get_image_func

        # Mock OpenAI client response using dependency override
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "A beautiful landscape with mountains and trees"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Override the dependency
        app.dependency_overrides[get_openai_client] = lambda: mock_client

        try:
            request_data = ImageCaptioningRequest(
                doc_id="doc123",
                image_id="img456",
                image_url="https://example.com/image.png",
                prompt="Describe this landscape",
            )

            response = client.post("/caption/", json=request_data.model_dump())

            assert response.status_code == 200
            response_data = response.json()
            assert "caption" in response_data
            assert (
                "A beautiful landscape with mountains and trees."
                in response_data["caption"]
            )
        finally:
            app.dependency_overrides.clear()

    @patch("routers.caption.get_image")
    def test_generate_image_caption_with_post_processing_disabled(self, mock_get_image):
        """Test image caption generation with post-processing disabled"""
        from shared_utils.openai_client import get_openai_client

        # Mock image retrieval as async
        async def mock_get_image_func(*args, **kwargs):
            return (b"mock_image_bytes", "png")

        mock_get_image.side_effect = mock_get_image_func

        # Mock OpenAI client response using dependency override
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "A beautiful landscape"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Override the dependency
        app.dependency_overrides[get_openai_client] = lambda: mock_client

        try:
            # Mock VLM config to disable post-processing
            with patch(
                "routers.caption.vlm_config.enable_response_post_processing", False
            ):
                request_data = ImageCaptioningRequest(
                    doc_id="doc123",
                    image_id="img456",
                    image_url="https://example.com/image.png",
                )

                response = client.post("/caption/", json=request_data.model_dump())

                assert response.status_code == 200
                response_data = response.json()
                # Without post-processing, no period should be added
                assert response_data["caption"] == "A beautiful landscape"
        finally:
            app.dependency_overrides.clear()

    def test_generate_image_caption_missing_image_url(self):
        """Test caption generation with missing image URL"""
        request_data = {
            "doc_id": "doc123",
            "image_id": "img456",
            "image_url": "",
            "prompt": "Describe this image",
        }

        response = client.post("/caption/", json=request_data)

        assert response.status_code == 422  # Pydantic validation error for empty string
        response_data = response.json()
        assert "Field cannot be empty" in str(response_data)

    @patch("routers.caption.get_image")
    def test_generate_image_caption_image_retrieval_error(self, mock_get_image):
        """Test caption generation when image retrieval fails"""

        # Mock async function with exception
        async def mock_get_image_error(*args, **kwargs):
            raise Exception("Failed to fetch image")

        mock_get_image.side_effect = mock_get_image_error

        request_data = ImageCaptioningRequest(
            doc_id="doc123",
            image_id="img456",
            image_url="https://example.com/image.png",
        )

        response = client.post("/caption/", json=request_data.model_dump())

        # The exception from get_image should propagate
        assert response.status_code == 500

    @patch("routers.caption.get_image")
    def test_generate_image_caption_openai_api_error(self, mock_get_image):
        """Test caption generation with OpenAI API error"""
        from shared_utils.openai_client import get_openai_client

        # Mock image retrieval as async
        async def mock_get_image_func(*args, **kwargs):
            return (b"mock_image_bytes", "png")

        mock_get_image.side_effect = mock_get_image_func

        # Mock OpenAI client to raise APIError using dependency override
        mock_client = AsyncMock()
        # Create a proper APIError - it needs a message and response/request parameters
        api_error = Exception(
            "API Error"
        )  # Use Exception to trigger the except block in the router
        mock_client.chat.completions.create = AsyncMock(side_effect=api_error)

        # Override the dependency
        app.dependency_overrides[get_openai_client] = lambda: mock_client

        try:
            request_data = ImageCaptioningRequest(
                doc_id="doc123",
                image_id="img456",
                image_url="https://example.com/image.png",
            )

            response = client.post("/caption/", json=request_data.model_dump())

            assert response.status_code == 500
            response_data = response.json()
            assert "HTTP error calling vLLM service" in response_data["detail"]
        finally:
            app.dependency_overrides.clear()

    @patch("routers.caption.get_image")
    def test_generate_image_caption_no_choices(self, mock_get_image):
        """Test caption generation when OpenAI returns no choices"""
        from shared_utils.openai_client import get_openai_client

        # Mock image retrieval as async
        async def mock_get_image_func(*args, **kwargs):
            return (b"mock_image_bytes", "png")

        mock_get_image.side_effect = mock_get_image_func

        # Mock OpenAI client response with no choices using dependency override
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = []
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Override the dependency
        app.dependency_overrides[get_openai_client] = lambda: mock_client

        try:
            request_data = ImageCaptioningRequest(
                doc_id="doc123",
                image_id="img456",
                image_url="https://example.com/image.png",
            )

            response = client.post("/caption/", json=request_data.model_dump())

            assert response.status_code == 500
            response_data = response.json()
            assert "No choices found in OpenAI response" in response_data["detail"]
        finally:
            app.dependency_overrides.clear()

    @patch("routers.caption.get_image")
    def test_generate_image_caption_malformed_choice(self, mock_get_image):
        """Test caption generation when OpenAI returns malformed choice"""
        from shared_utils.openai_client import get_openai_client

        # Mock image retrieval as async
        async def mock_get_image_func(*args, **kwargs):
            return (b"mock_image_bytes", "png")

        mock_get_image.side_effect = mock_get_image_func

        # Mock OpenAI client response with malformed choice using dependency override
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Override the dependency
        app.dependency_overrides[get_openai_client] = lambda: mock_client

        try:
            request_data = ImageCaptioningRequest(
                doc_id="doc123",
                image_id="img456",
                image_url="https://example.com/image.png",
            )

            response = client.post("/caption/", json=request_data.model_dump())

            assert response.status_code == 500
            response_data = response.json()
            assert "Malformed choice in OpenAI response" in response_data["detail"]
        finally:
            app.dependency_overrides.clear()

    @patch("routers.caption.get_image")
    def test_generate_image_caption_none_content(self, mock_get_image):
        """Test caption generation when OpenAI returns None content"""
        from shared_utils.openai_client import get_openai_client

        # Mock image retrieval as async
        async def mock_get_image_func(*args, **kwargs):
            return (b"mock_image_bytes", "png")

        mock_get_image.side_effect = mock_get_image_func

        # Mock OpenAI client response with None content using dependency override
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Override the dependency
        app.dependency_overrides[get_openai_client] = lambda: mock_client

        try:
            request_data = ImageCaptioningRequest(
                doc_id="doc123",
                image_id="img456",
                image_url="https://example.com/image.png",
            )

            response = client.post("/caption/", json=request_data.model_dump())

            assert response.status_code == 500
            response_data = response.json()
            assert "Malformed choice in OpenAI response" in response_data["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_generate_image_caption_invalid_request(self):
        """Test caption generation with invalid request data"""
        invalid_data = {
            "doc_id": "doc123"
            # Missing required fields
        }

        response = client.post("/caption/", json=invalid_data)

        assert response.status_code == 422  # Validation error

    @patch("routers.caption.get_image")
    def test_generate_image_caption_with_default_prompt(self, mock_get_image):
        """Test caption generation using default prompt"""
        from shared_utils.openai_client import get_openai_client

        # Mock image retrieval as async
        async def mock_get_image_func(*args, **kwargs):
            return (b"mock_image_bytes", "png")

        mock_get_image.side_effect = mock_get_image_func

        # Mock OpenAI client response using dependency override
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Default caption"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Override the dependency
        app.dependency_overrides[get_openai_client] = lambda: mock_client

        try:
            request_data = ImageCaptioningRequest(
                doc_id="doc123",
                image_id="img456",
                image_url="https://example.com/image.png",
                # No prompt specified, should use default
            )

            response = client.post("/caption/", json=request_data.model_dump())

            assert response.status_code == 200
            response_data = response.json()
            assert "caption" in response_data
        finally:
            app.dependency_overrides.clear()
