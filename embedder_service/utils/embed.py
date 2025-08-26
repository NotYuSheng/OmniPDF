# For data chunking and embedding
from fastapi import HTTPException
from typing import List, Dict, Any
import logging
from datetime import timedelta

from models.embed import ProcessingConfig
from models.helper import get_embedding_model
from shared_utils.chroma_client import get_chroma_client
from shared_utils.redis import RedisSimpleFileFlag

logger = logging.getLogger(__name__)
redis_flag_store = RedisSimpleFileFlag(
    prefix="ChromaDB", default_expiry=timedelta(hours=1)
)


async def vectorize_chromadb(chunk_data: List[Dict[str, Any]], config: ProcessingConfig, collection_name:str):
    """Embed data chunks of PDF document into ChromaDB AsyncHTTPClient instance"""

    logger.info("Starting embedding process...")
    embedding_model = get_embedding_model(config.embedding_model)

    try:
        # Connect to ChromaDB AsyncHTTPClient instance and retrieve/create specified database collection
        logger.info("Getting collection...")
        chroma_client = await get_chroma_client()
        collection = await chroma_client.get_or_create_collection(name=collection_name, embedding_function=embedding_model)
        logger.info(f"Using existing collection: {collection_name}")

        # Split each chunk based on 'chunk_id', 'content' and 'metadata' keys 
        # and append the values into 3 distinct lists to be embedded into ChromaDB
        ids = [chunk['chunk_id'] for chunk in chunk_data]
        documents = [chunk['content'] for chunk in chunk_data]
        metadatas = [chunk['metadata'] for chunk in chunk_data]

        if not ids:
            logger.warning("No chunks to add to the collection.")
            return
        
        # Embed into ChromaDB using specified embedding model
        await collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        for doc_id in set([metadata["doc_id"] for metadata in metadatas]):
            redis_flag_store[doc_id] = 1
        logger.info(f"Added {len(ids)} chunks to collection '{collection_name}'")

        return {
            "collection_name": collection_name,
            "total_chunks_added": len(chunk_data)
        }

    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise HTTPException(status_code=500, detail="Embedding failed")
    