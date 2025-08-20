from fastapi import FastAPI
from routers import metadata, wordcloud
from routers import health

import logging

# Set up logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(root_path="/metadata")

app.include_router(health.router)
app.include_router(metadata.router)
app.include_router(wordcloud.router)
