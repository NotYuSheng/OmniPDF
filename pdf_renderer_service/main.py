from fastapi import FastAPI
from routers import health, render, bypass
import logging

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(root_path="/pdf_renderer")

app.include_router(health.router)
app.include_router(render.router)
app.include_router(bypass.router)
