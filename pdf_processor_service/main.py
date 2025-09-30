from fastapi import FastAPI
from routers import health
from routers import document, images, session, tables, text_chunks, json_data, embed, metadata, wordcloud, extractor, translation, renderer
from prometheus_fastapi_instrumentator import Instrumentator

import logging

# Set up logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(root_path="/pdf_processor")

# Initialize Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

app.include_router(health.router)
app.include_router(document.router)
app.include_router(session.router)
app.include_router(images.router)
app.include_router(tables.router)
app.include_router(text_chunks.router)
app.include_router(json_data.router)
app.include_router(embed.router)
app.include_router(extractor.router)
app.include_router(metadata.router)
app.include_router(wordcloud.router)
app.include_router(translation.router)
app.include_router(renderer.router)
