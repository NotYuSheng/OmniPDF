from fastapi import APIRouter, HTTPException, Depends
from openai import AsyncOpenAI, APIError
from PIL import Image
import logging
import httpx
import io
import base64

from models.caption import ImageCaptioningRequest, ImageCaptioningResponse
from shared_utils.openai_client import get_openai_client
from models.vlm_config import PromptTemplates, VLMConfig, CaptionOptimizer

router = APIRouter(prefix="/caption", tags=["caption"])
logger = logging.getLogger(__name__)

http_client = httpx.AsyncClient()
vlm_config = VLMConfig()
VLM_MODEL = vlm_config.model_name


async def get_image(image_url: str) -> tuple[bytes, str]:
    """Retrieve image from processed PDF document"""

    try:
        response = await http_client.get(image_url, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.error(f"Invalid or expired S3 signed URL: {e.response.status_code}")
            raise HTTPException(status_code=400, detail="Invalid or expired S3 signed URL")
        else:
            logger.error(f"Error fetching image: {e.response.status_code}")
            raise HTTPException(status_code=500, detail="Failed to fetch image")
    except httpx.RequestError as e:
        logger.error(f"Error fetching image: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch image")

    try:
        image_bytes = response.content
        # Get image format
        image = Image.open(io.BytesIO(image_bytes))
        image_format = image.format.lower() if image.format else "jpeg"
        # (Optional): Set mode of image
        # if image.mode != "RGB":
        #     image = image.convert("RGB")

        logger.info("Successfully downloaded and processed image.")
        return image_bytes, image_format

    except (Image.UnidentifiedImageError, IOError) as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail="Failed to process image")


@router.post("/", response_model=ImageCaptioningResponse, status_code=200)
async def generate_image_caption(
    request: ImageCaptioningRequest, 
    client: AsyncOpenAI = Depends(get_openai_client)
):
    """Use Vision-Language Model (VLM) to create a caption for the retrieved image from the processed PDF"""
    
    logger.info(f"Generating caption with given prompt: '{request.prompt}'")

    image_url = request.image_url
    if not image_url:
        logger.error("Image URL is required for caption generation.")
        raise HTTPException(status_code=400, detail="Image URL is required")

    try:
        image_bytes, image_format = await get_image(image_url)
        
        # Base64 encode the image
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        logger.info("Image successfully encoded to base64.")

        # Prepare messages containing system prompt and encoded image for VLM
        system_prompt = PromptTemplates.get_system_prompt()
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": request.prompt},
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/{image_format};base64,{encoded_image}"}
                    }
                ]
            }
        ]

        logger.info(f"Sending request to {VLM_MODEL} with {len(messages)} messages")
        response = await client.chat.completions.create(
            model=VLM_MODEL,
            messages=messages,
            **vlm_config.generation_params
        )
        
    except APIError as e:
        logger.error(f"HTTP error calling vLLM service: {e}")
        raise HTTPException(status_code=500, detail="HTTP error calling vLLM service")
    except Exception as e:
        logger.error(f"An unexpected error occurred during caption generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during caption generation.")

    if not response.choices:
        logger.error("No choices found in OpenAI response: %s", response)
        raise HTTPException(
            status_code=500,
            detail="No choices found in OpenAI response",
        )

    first_choice = response.choices[0]
    if not first_choice.message or first_choice.message.content is None:
        logger.error("Malformed choice in OpenAI response: %s", first_choice)
        raise HTTPException(
            status_code=500,
            detail="Malformed choice in OpenAI response",
        )
    
    # Post-process the response
    if vlm_config.enable_response_post_processing:
        processed_caption = CaptionOptimizer.post_process_llm_response(first_choice.message.content)
    else:
        processed_caption = first_choice.message.content
    
    logger.info(f"Received caption from LLM: '{processed_caption}'")

    response_data = ImageCaptioningResponse(caption=processed_caption)
    logger.info("Successfully generated caption and sending response.")
    return response_data
