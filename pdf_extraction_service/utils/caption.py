from os import environ
import logging
import httpx

logger = logging.getLogger(__name__)
IMAGE_CAPTIONER_URL = environ["IMAGE_CAPTIONER_URL"]


async def get_caption(image_url: str) -> str:
    payload = {
        "doc_id": "temp_doc",
        "image_id": "temp_image",
        "image_url": image_url
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{IMAGE_CAPTIONER_URL}/caption/", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("caption", "")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error retrieving caption: {e}")
            return ""
        except httpx.RequestError as e:
            logger.error(f"Request error retrieving caption: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error retrieving caption: {e}", exc_info=True)
            return ""