from fastapi import FastAPI
from routers import health, semantic, sentence
import nltk
import logging


# Set up logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI."""
    nltk.download("punkt_tab")
    yield  # This is where you can add startup and shutdown events if needed


app = FastAPI(root_path="/embedder", lifespan=lifespan)

app.include_router(health.router)
app.include_router(semantic.router)
app.include_router(sentence.router)
