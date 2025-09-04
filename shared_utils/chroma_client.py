import chromadb
import os

# For data chunking and embedding
import logging

from shared_utils.redis import RedisDocumentFileList

logger = logging.getLogger(__name__)

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = os.getenv("CHROMADB_PORT", "8000")

TEXTUAL_EMBEDDING_COLLECTION = "SentenceEmbeds"
MAX_CHUNK_PER_RETRIVAL = int(os.getenv("MAX_CHUNK_PER_RETRIVAL", "100"))

document_list = RedisDocumentFileList()


async def get_chroma_client():
    """
    Initialize and return an AsyncHTTPClient ChromaDB client instance.
    """
    chroma_client = await chromadb.AsyncHttpClient(
        host=CHROMADB_HOST, port=int(CHROMADB_PORT)
    )
    return chroma_client


async def query_chroma(doc_id: str, collection_name: str, query: str, max_results: int = 5):
    chroma_client = await get_chroma_client()
    # Step 1: Retrieve relevant chunks from ChromaDB
    collection = await chroma_client.get_collection(collection_name)

    query_params = {
        "query_texts": [query],
        "n_results": max_results,
        "include": ["distances", "documents", "metadatas", "embeddings"],
    }

    if doc_id:
        query_params["where"] = {"doc_id": doc_id}
        logger.info(f"Filtering results to document ID: {doc_id}")
        document_list[doc_id]
    else:
        logger.info("Searching across all documents in collection")

    return await collection.query(**query_params)


async def get_chunks(doc_id: str):
    chroma_client = await get_chroma_client()
    collection = await chroma_client.get_collection(TEXTUAL_EMBEDDING_COLLECTION)
    offset = 0
    results = await collection.get(
        where={"doc_id": doc_id}, limit=MAX_CHUNK_PER_RETRIVAL, offset=offset
    )
    logger.info(results)
    chunks = []
    while results["documents"]:
        offset += MAX_CHUNK_PER_RETRIVAL
        chunks.extend(results["documents"])
        results = await collection.get(
            where={"doc_id": doc_id}, limit=MAX_CHUNK_PER_RETRIVAL, offset=offset
        )

    document_list[doc_id]
    return chunks
