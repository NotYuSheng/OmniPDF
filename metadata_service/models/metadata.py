from pydantic import BaseModel


class MetadataRequest(BaseModel):
    """
    Request model for chat API endpoints.
    """

    doc_id: str
