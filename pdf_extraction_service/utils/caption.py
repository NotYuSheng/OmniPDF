from os import environ
import logging
import httpx

logger = logging.getLogger(__name__)
IMAGE_CAPTIONER_URL = environ["IMAGE_CAPTIONER_URL"]


async def get_caption(doc_id: str, image_id: str, image_url: str) -> str:
    payload = {
        "doc_id": doc_id,
        "image_id": image_id,
        "image_url": image_url
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=60.0, read=120.0, write=60.0, pool=60.0)) as client:
        try:
            response = await client.post(f"{IMAGE_CAPTIONER_URL}/caption/", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("caption", "")
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(f"HTTP error retrieving caption for image {image_id}: {type(e).__name__}: {e}", exc_info=True)
            return ""
        except Exception as e:
            logger.error(f"Unexpected error retrieving caption: {e}", exc_info=True)
            return ""