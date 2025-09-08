from pydantic import BaseModel, HttpUrl
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


class AnnotationResponse(BaseModel):
    doc_id: str
    docling: Optional[DoclingTranslationResponse] = None
