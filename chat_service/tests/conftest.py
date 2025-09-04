# Simple conftest.py for unit tests - keeps existing unit tests working
import sys
import os
from unittest.mock import MagicMock, patch
import pytest

# Set up environment variables for unit testing (mocked)
os.environ.update(
    {
        "MODEL_TOP_K": "5",
        "OPENAI_API_KEY": "test-key-mock-only",
        "OPENAI_BASE_URL": "http://mock-openai:8999/v1",
        "CHROMA_HOST": "mock-chromadb",
        "CHROMA_PORT": "8000",
    }
)

# Mock heavy dependencies for unit tests
HEAVY_DEPS = ["chromadb", "sentence_transformers", "torch", "transformers", "numpy"]

for dep in HEAVY_DEPS:
    if dep not in sys.modules:
        sys.modules[dep] = MagicMock()


@pytest.fixture(autouse=True)
def mock_all_external_services():
    """Mock all external service dependencies for unit tests"""
    with (
        patch("shared_utils.openai_client.get_openai_client") as mock_openai,
        patch("shared_utils.chroma_client.get_chroma_client") as mock_chroma,
        patch("openai.AsyncOpenAI") as mock_openai_class,
    ):
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create = MagicMock()
        mock_openai.return_value = mock_openai_client
        mock_openai_class.return_value = mock_openai_client

        mock_chroma_client = MagicMock()
        mock_chroma.return_value = mock_chroma_client

        yield {
            "openai": mock_openai_client,
            "chroma": mock_chroma_client,
        }
