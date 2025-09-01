from pydantic import BaseModel, Field


class ImageCaptioningRequest(BaseModel):
    doc_id: str
    image_id: str
    image_url: str
    prompt: str = Field(default="Generate a descriptive caption for this image.", description="Prompt to guide the caption generation")


class ImageCaptioningResponse(BaseModel):
    caption: str
