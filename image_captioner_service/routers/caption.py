from fastapi import APIRouter, HTTPException, Depends
from openai import AsyncOpenAI, APIError
import logging
import httpx
from PIL import Image
import io
import base64

from models.caption import ImageCaptioningRequest, ImageCaptioningResponse
from shared_utils.openai_client import get_openai_client
from models.vlm_config import PromptTemplates, VLMConfig, CaptionOptimizer

router = APIRouter(prefix="/caption", tags=["caption"])
logger = logging.getLogger(__name__)

# Initialize configuration for VLM
vlm_config = VLMConfig()
prompt_templates = PromptTemplates()
optimizer = CaptionOptimizer()

VLM_MODEL = vlm_config.model_name


@router.post("/", response_model=ImageCaptioningResponse, status_code=200)
async def generate_image_caption(request: ImageCaptioningRequest, client: AsyncOpenAI = Depends(get_openai_client)):

    logger.info(f"Generating caption with given prompt: '{request.prompt}'")

    image_url = request.image_url
    if not image_url:
        logger.error("Image URL is required for caption generation.")
        raise HTTPException(status_code=400, detail="Image URL is required")

    try:
        logger.info(f"doc id: {request.doc_id}")
        logger.info(f"Image ID: {request.image_id}")
        logger.info(f"Image URL: {request.image_url}")
        logger.info(f"prompt: {request.prompt}")

        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(request.image_url, follow_redirects=True)

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
        image = Image.open(io.BytesIO(response.content))
        if image.mode != "RGB":
            logger.info("Converting image to RGB mode.")
            image = image.convert("RGB")
        
        # Convert the image to bytes
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="JPEG")
        image_bytes = image_bytes.getvalue()

        logger.info("Successfully downloaded and processed image.")

    except (Image.UnidentifiedImageError, IOError) as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail="Failed to process image")
    
    try:
        # Base64 encode the image
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        system_prompt = prompt_templates.get_system_prompt()
        
        # Prepare messages containing system prompt and encoded image for VLM
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": request.prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
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
        processed_caption = optimizer.post_process_llm_response(first_choice.message.content)
    else:
        processed_caption = first_choice.message.content
    
    logger.info(f"Received caption from LLM: '{processed_caption}'")

    response_data = ImageCaptioningResponse(doc_id=request.doc_id, image_id=request.image_id, caption=processed_caption)
    logger.info("Successfully generated caption and sending response.")

    return response_data

