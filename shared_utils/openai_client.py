from openai import AsyncOpenAI
import os


def get_openai_client() -> AsyncOpenAI:
    """
    Initialize and return an OpenAI client instance.
    """
    return AsyncOpenAI(
        base_url=os.environ["OPENAI_BASE_URL"],  # Make sure `/v1` is included
        api_key=os.environ["OPENAI_API_KEY"],
    )
