from pydantic import BaseModel, Field
from typing import Optional, List, Any


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


class TranslationRequest(BaseModel):
    source_lang: str = Field(min_length=1, description="Source language")
    target_lang: str = Field(min_length=1, description="Target language")


class TranslationResponse(BaseModel):
    doc_id: str = Field(min_length=1, description="Document ID")
    status: str = Field(description="Translation status")
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    result: Optional[DoclingTranslationResponse] = None