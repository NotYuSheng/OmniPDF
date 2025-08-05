from fastapi import FastAPI
from routers import health
from routers import document, images, session, tables, text_chunks, json_data
import logging

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(root_path="/pdf_processor")

app.include_router(health.router)
app.include_router(document.router)
app.include_router(session.router)
app.include_router(images.router)
app.include_router(tables.router)
app.include_router(text_chunks.router)
app.include_router(json_data.router)
