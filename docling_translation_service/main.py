from fastapi import FastAPI
from routers import health
from docling_translation_service.routers import translation
from prometheus_fastapi_instrumentator import Instrumentator
import logging

# Set up logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(root_path="/docling_translation")

# Initialize Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

app.include_router(health.router)
app.include_router(translation.router)
