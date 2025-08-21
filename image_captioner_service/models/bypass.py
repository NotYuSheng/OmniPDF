from pydantic import BaseModel, HttpUrl
from typing import Optional

class ImageBypassResponse(BaseModel):
    doc_id: str
    image_id: str
    image_url: Optional[HttpUrl]
    