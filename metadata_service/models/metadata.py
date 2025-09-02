from pydantic import BaseModel


class MetadataRequest(BaseModel):
    """
    Request model for metadata API endpoints.
    """

    doc_id: str
