from pydantic import BaseModel
from typing import Optional, List


class MetadataRequest(BaseModel):
    """
    Request model for metadata API endpoints.
    """
    doc_id: str


class MetadataResult(BaseModel):
    """
    Model for metadata result data.
    """
    filename: Optional[str] = None
    summary: Optional[str] = None
    executive_summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    authors: Optional[List[str]] = None
    title: Optional[str] = None


class MetadataResponse(BaseModel):
    """
    Response model for metadata endpoints.
    """
    doc_id: str
    status: str
    result: Optional[MetadataResult] = None
