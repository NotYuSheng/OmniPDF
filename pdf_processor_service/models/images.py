from pydantic import BaseModel


class ImageData(BaseModel):
    image_key: str
    url: str


class ImageResponse(BaseModel):
    doc_id: str
    filename: str
    images: list[ImageData]
