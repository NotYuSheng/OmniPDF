from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Any

class DocumentRendererResponse(BaseModel):
    doc_id: str
    filename: str
    download_url: Optional[HttpUrl]

class DoclingTranslationResponse(BaseModel):
    schema_name: str
    version: str 
    name: str 
    origin: Any
    furniture: Any
    texts: List[Any]
    pictures: List[Any]
    tables: List[Any]
    key_value_items: List[Any]
    form_items: List[Any]
    pages: Any

class AnnotationResponse(BaseModel):
    doc_id: str
    docling: Optional[DoclingTranslationResponse] = None
    source_lang: str
    target_lang: str