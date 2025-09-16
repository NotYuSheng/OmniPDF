from pydantic import BaseModel
from typing import Optional, List


class MetadataData(BaseModel):
    """Model for metadata content."""
    filename: Optional[str] = None
    summary: Optional[str] = None
    executive_summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    authors: Optional[List[str]] = None
    title: Optional[str] = None


class MetadataResponse(BaseModel):
    """Response model for metadata endpoints."""
    doc_id: str
    status: str
    metadata: Optional[MetadataData] = None


class WordcloudResponse(BaseModel):
    """Response model for wordcloud endpoint."""
    doc_id: str
    top_words: List[str]