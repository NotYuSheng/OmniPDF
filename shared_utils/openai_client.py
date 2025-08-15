from openai import AsyncOpenAI
import os


def get_openai_client() -> AsyncOpenAI:
    """
    Initialize and return an OpenAI client instance.
    """
    return AsyncOpenAI(
        base_url=os.getenv("LLM_API_URL"), # Make sure `/v1` is included
        api_key=os.getenv("OPENAI_API_KEY"),
    )
