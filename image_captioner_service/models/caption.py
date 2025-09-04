from pydantic import BaseModel, Field, field_validator


class ImageCaptioningRequest(BaseModel):
    doc_id: str
    image_id: str
    image_url: str
    prompt: str = Field(
        default="Generate a descriptive caption for this image.",
        description="Prompt to guide the caption generation",
    )

    @field_validator("doc_id", "image_id", "image_url")
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v


class ImageCaptioningResponse(BaseModel):
    caption: str
