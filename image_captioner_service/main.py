from fastapi import FastAPI
from routers import health, caption
import logging

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(root_path="/image_captioner")

app.include_router(health.router)
app.include_router(caption.router)
