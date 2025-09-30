from pydantic import BaseModel, Field
from typing import List, Dict, Any


class ChatRequest(BaseModel):
    """
    Request model for chat API endpoints.
    """

    message: str
    session_id: str
    doc_ids: List[str] = None
    collection_name: str = Field(default="default_collection", description="ChromaDB collection name")


class ChatResponse(BaseModel):
    """
    Response model for chat API
    """

    response: str
    relevant_chunks: List[Dict[str, Any]] = Field(
        default_factory=list, description="Additional metadata about the RAG process"
    )
    metadata: Dict[str, Any]
