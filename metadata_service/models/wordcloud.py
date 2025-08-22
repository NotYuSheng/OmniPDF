from pydantic import BaseModel


class WordcloudResponse(BaseModel):
    """
    Response model for wordcloud API endpoints.
    """

    doc_id: str
    top_words: list[str]
