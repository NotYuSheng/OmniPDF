import chromadb
import os

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = os.getenv("CHROMADB_PORT", "8000")


async def get_chroma_client():
    """
    Initialize and return an AsyncHTTPClient ChromaDB client instance.
    """
    chroma_client = await chromadb.AsyncHttpClient(host=CHROMADB_HOST, port=int(CHROMADB_PORT))
    return chroma_client
