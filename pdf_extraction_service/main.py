from fastapi import FastAPI
from routers import health, extractor
from prometheus_fastapi_instrumentator import Instrumentator
import logging

# Set up logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(root_path="/pdf_extraction")

# Initialize Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

app.include_router(health.router)
app.include_router(extractor.router)
