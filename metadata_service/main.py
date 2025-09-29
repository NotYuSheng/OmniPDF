from fastapi import FastAPI
from routers import metadata, wordcloud
from routers import health
from prometheus_fastapi_instrumentator import Instrumentator

import logging

# Set up logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(root_path="/metadata")

# Initialize Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

app.include_router(health.router)
app.include_router(metadata.router)
app.include_router(wordcloud.router)
