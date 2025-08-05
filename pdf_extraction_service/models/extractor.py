from pydantic import BaseModel
from typing import Optional, List, Any

class PDFDataResponse(BaseModel):
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

class ExtractResponse(BaseModel):
    doc_id: str
    status: str
    result: Optional[PDFDataResponse] = None