# For data chunking and embedding

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging
import uuid

from models.embed import DataRequest
from models.helper import get_chunking_model
from shared_utils.chroma_client import get_chroma_client
from langchain_core.documents import Document
from utils.embed import vectorize_chromadb

router = APIRouter(prefix="/semantic", tags=["semantic"])

logger = logging.getLogger(__name__)

SEMANTIC_EMBEDDING_COLLECTION = "SemanticEmbeds"


async def data_chunking(request: DataRequest) -> List[Dict[str, Any]]:
    """Perform chunking / splitting of data via Semantic Chunking using LangChain's SemanticChunker,
    and reject by returning empty list if PDF document has no textual content"""

    logger.info("Starting chunking process...")

    try:
        chunker = get_chunking_model(request.config)
        if not request.text.strip():
            raise HTTPException(
                status_code=400, detail="No textual content found in PDF"
            )

        # Create a Document object for textual data to be chunked
        doc = Document(page_content=request.text.strip())

        chunks = chunker.split_documents([doc])
        logger.info(f"Number of chunks: {len(chunks)}")

        chunk_data = []
        current_pos = 0

        for i, chunk in enumerate(chunks):
            # First iteration: Extract first chunk of doc.page_content
            chunk_content = chunk.page_content
            logger.info(f"Length of chunk {i + 1}: {len(chunk_content.strip())}")

            chunk_start = request.text.find(chunk_content, current_pos)

            if chunk_start == -1:
                chunk_start = current_pos

            chunk_end = chunk_start + len(chunk_content)

            # # Find which page this chunk belongs to
            # page_number = None
            # for page_info in request.pages_info:
            #     if (chunk_start >= page_info['char_start'] and
            #             chunk_start < page_info['char_end']):
            #         page_number = page_info['page_number']
            #         break

            # Find page number for the chunk
            # page_number = None
            # for page_info in request.pages_info:
            #     # Ensure keys exist to avoid KeyErrors
            #     page_start = page_info.get('start_char')
            #     page_end = page_info.get('end_char')
            #     if page_start is not None and page_end is not None:
            #         if page_start <= chunk_start < page_end:
            #             page_number = page_info.get('page')
            #             break

            # Include doc_id in metadata of each chunk
            chunk_metadata = chunk.metadata.copy()
            chunk_metadata["doc_id"] = request.doc_id
            chunk_metadata["session_id"] = request.session_id

            # Skip chunks that are too small or too large
            # if (len(chunk_content.strip()) < request.config.min_chunk_size) or (len(chunk_content.strip()) > request.config.max_chunk_size):
            #     current_pos = chunk_end
            #     continue

            # else:
            chunk_data.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "content": chunk_content.strip(),
                    "start_char": chunk_start,
                    "end_char": chunk_end,
                    "page_number": None,
                    "chunk_index": len(chunk_data),
                    "metadata": chunk_metadata,
                }
            )

            current_pos = chunk_end

        logger.info(chunk_data)
        return chunk_data
    except HTTPException:
        # Re-raise HTTPExceptions (like 400 Bad Request) as-is
        raise
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        raise HTTPException(status_code=500, detail="Chunking failed.")


@router.post("/")
async def pdf_embedder_service(request: DataRequest):
    "Chunk up and embed data from PDF document into ChromaDB AsyncHTTPClient instance"

    try:
        # Extracted data has to be chunked up first
        chunk_data = await data_chunking(request)

        if not chunk_data:
            raise HTTPException(
                status_code=400, detail="No chunks were created from the input text"
            )

        # Once chunking is done, embed into ChromaDB with the specified embedding model
        embed_results = await vectorize_chromadb(
            chunk_data, request.config, SEMANTIC_EMBEDDING_COLLECTION
        )

        return {
            "status": "success",
            "doc_id": request.doc_id,
            "chunks_created": len(chunk_data),
            "embedding_results": embed_results,
            "chunk_details": [
                {
                    "chunk_id": chunk["chunk_id"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "content_length": len(chunk["content"]),
                    "start_char": chunk["start_char"],
                    "end_char": chunk["end_char"],
                }
                for chunk in chunk_data
            ],
        }
    except HTTPException:
        # Re-raise HTTPExceptions (like 400 Bad Request) as-is
        raise
    except Exception as e:
        logger.error(f"PDF embedder service failed: {e}")
        raise HTTPException(status_code=500, detail="PDF embedder service failed")


@router.get("/status/{doc_id}")
async def verify_document_embedding(doc_id: str):
    """Verify if a document's data chunks have been successfully embedded into ChromaDB AsyncHTTPClient instance"""

    try:
        # Retrieve database collection from ChromaDB
        chroma_client = await get_chroma_client()
        collection = await chroma_client.get_collection(SEMANTIC_EMBEDDING_COLLECTION)

        # Query by doc_id of each chunk
        results = await collection.get(
            where={"doc_id": doc_id}, include=["documents", "metadatas", "embeddings"]
        )

        if not results["ids"]:
            return {
                "doc_id": doc_id,
                "status": "not_found",
                "chunks_found": 0,
                "message": f"No chunks found for document {doc_id}",
            }

        return {
            "doc_id": doc_id,
            "status": "found",
            "chunks_found": len(results["ids"]),
            "chunk_ids": results["ids"],
            "chunks_have_embeddings": len(results.get("embeddings", [])) > 0,
            "sample_content": results["documents"] if results["documents"] else None,
        }

    except Exception as e:
        logger.error(f"Document verification failed: {e}")
        raise HTTPException(status_code=500, detail="Document verification failed")
