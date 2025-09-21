from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict


class DocumentRendererResponse(BaseModel):
    doc_id: str
    filename: str
    download_url: Optional[HttpUrl] = None


class DoclingTranslationResponse(BaseModel):
    schema_name: str
    version: str
    name: str
    origin: Dict
    furniture: Dict
    texts: List[Dict]
    pictures: List[Dict]
    tables: List[Dict]
    key_value_items: List[Dict]
    form_items: List[Dict]
    pages: Dict


class RendererResponse(BaseModel):
    doc_id: str = Field(min_length=1, description="Document ID")
    status: str = Field(description="Rendering status")
    result: Optional[DocumentRendererResponse] = None