from pydantic import BaseModel


class WordcloudResponse(BaseModel):
    """
    Response model for chat API endpoints.
    """

    doc_id: str
    top_words: list[str]
