from pydantic import BaseModel

class ImageCaptioningRequest(BaseModel):
    doc_id: str
    image_id: str
    image_url: str
    prompt: str


class ImageCaptioningResponse(BaseModel):
    doc_id: str
    image_id: str
    caption: str
