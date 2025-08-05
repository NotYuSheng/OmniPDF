from openai import OpenAI
import os


def get_openai_client() -> OpenAI:
    """
    Initialize and return an OpenAI client instance.
    """
    return OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL"),  # Make sure `/v1` is included
        api_key=os.getenv("OPENAI_API_KEY"),
    )
