from openai import AsyncOpenAI
import os


def get_openai_client() -> AsyncOpenAI:
    """
    Initialize and return an OpenAI client instance.
    """
    return AsyncOpenAI(
        # base_url=os.getenv("OPENAI_BASE_URL"),  # Make sure `/v1` is included
        base_url=os.getenv("LLM_API_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
