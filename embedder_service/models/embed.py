from pydantic import BaseModel, Field
from typing import List, Dict, Optional, get_args
import os
from langchain_experimental.text_splitter import BreakpointThresholdType

_EMBEDDING_MODEL_DEFAULT = "all-MiniLM-L6-v2"
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", _EMBEDDING_MODEL_DEFAULT)

breakpoints = get_args(BreakpointThresholdType)


class ProcessingConfig(BaseModel):
    """Config model for embed API endpoint."""

    chunk_size: int = Field(
        default=512, description="Target chunk size in characters")
    overlap: int = Field(
        default=50, description="Overlap between chunks in characters")
    embedding_model: str = Field(
        default=EMBEDDING_MODEL_NAME, description="Sentence Transformer model")
    breakpoint_threshold_type: BreakpointThresholdType = Field(
        default=breakpoints[0], description="Breakpoint threshold type")
    breakpoint_threshold_amount: Optional[float] = Field(
        default=90.0, description="Breakpoint threshold amount")
    min_chunk_size: int = Field(default=100, description="Minimum chunk size")
    max_chunk_size: int = Field(default=1000, description="Maximum chunk size")
    store_in_chroma: bool = Field(
        default=True, description="Store embeddings in ChromaDB")
    collection_name: str = Field(
        default="my_documents", description="ChromaDB collection name")


class DataRequest(BaseModel):
    """Request model for embed API endpoint."""
    
    doc_id: str
    session_id: str
    text: str
    config: ProcessingConfig
    pages_info: List[Dict]
