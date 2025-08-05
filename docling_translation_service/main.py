from fastapi import FastAPI
from routers import health
from docling_translation_service.routers import translation
import logging

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(root_path="/docling_translation")

app.include_router(health.router)
app.include_router(translation.router)
