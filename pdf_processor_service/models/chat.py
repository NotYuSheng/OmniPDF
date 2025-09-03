from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

SEMANTIC_EMBEDDING_COLLECTION = "SemanticEmbeds"
TEXTUAL_EMBEDDING_COLLECTION = "SentenceEmbeds"


class ChatRequest(BaseModel):
    """
    Request model for chat API endpoints.
    """
    message: str
    doc_ids: list[str] = None
    collection_name: Optional[str] = Field(default=SEMANTIC_EMBEDDING_COLLECTION, description="ChromaDB collection name")


class ChatResponse(BaseModel):
    """
    Response model for chat API
    """
    response: str
    relevant_chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Additional metadata about the RAG process")
    metadata: Dict[str, Any]