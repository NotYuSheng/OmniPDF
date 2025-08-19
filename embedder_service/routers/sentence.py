# For data chunking and embedding

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging
import uuid

from models.embed import DataRequest
from shared_utils.chroma_client import get_chroma_client
from utils.embed import vectorize_chromadb
from nltk.tokenize import sent_tokenize

router = APIRouter(prefix="/sentence", tags=["sentence"])

logger = logging.getLogger(__name__)

# For English, 1 word is ~1.33 tokens, so for max of 4092 tokens, we use 4096 * (3/4) = 3072 words
MAX_STRING_LENGTH = 3072
TEXTUAL_EMBEDDING_COLLECTION = "SentenceEmbeds"

def split_in_segments_by_sentences(text:str, max_length:int):
    word_count = 0
    current_segment_sentences = []
    segments = []
    for sentence in sent_tokenize(text):
        new_word_count = len(sentence.split())
        word_count += new_word_count
        current_segment_sentences.append(sentence.strip())
        if word_count > max_length:
            segments.append(" ".join(current_segment_sentences))
            current_segment_sentences = []
            word_count = 0
    if current_segment_sentences:
        segments.append(" ".join(current_segment_sentences))
    return segments


async def token_data_chunking(request: DataRequest) -> List[Dict[str, Any]]:
    """Perform chunking / splitting of data via sentences,
    and reject by returning empty list if PDF document has no textual content"""

    logger.info("Starting chunking process...")

    try:
        if not request.text.strip():
            raise HTTPException(
                status_code=400, detail="No textual content found in PDF"
            )

        chunks = split_in_segments_by_sentences(request.text, MAX_STRING_LENGTH)
        logger.info(f"Number of chunks: {len(chunks)}")

        chunk_data = []
        current_pos = 0

        for i, chunk in enumerate(chunks):
            # First iteration: Extract first chunk of doc.page_content
            chunk_content = chunk
            logger.info(f"Length of chunk {i + 1}: {len(chunk_content.strip())}")

            chunk_start = request.text.find(chunk_content, current_pos)

            if chunk_start == -1:
                chunk_start = current_pos

            chunk_end = chunk_start + len(chunk_content)

            # Include doc_id and session_id in metadata of each chunk
            chunk_metadata = {}
            chunk_metadata["doc_id"] = request.doc_id
            chunk_metadata["session_id"] = request.session_id

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
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        raise HTTPException(status_code=500, detail="Chunking failed.")


@router.post("/")
async def pdf_embedder_service(request: DataRequest):
    "Chunk up and embed data from PDF document into ChromaDB AsyncHTTPClient instance"

    try:
        # Extracted data has to be chunked up first
        chunk_data = await token_data_chunking(request)

        if not chunk_data:
            raise HTTPException(
                status_code=400, detail="No chunks were created from the input text"
            )

        # Once chunking is done, embed into ChromaDB with the specified embedding model
        embed_results = await vectorize_chromadb(chunk_data, request.config, TEXTUAL_EMBEDDING_COLLECTION)

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
    except Exception as e:
        logger.error(f"PDF embedder service failed: {e}")
        raise HTTPException(status_code=500, detail="PDF embedder service failed")


@router.get("/status/{doc_id}")
async def verify_document_embedding(doc_id: str):
    """Verify if a document's data chunks have been successfully embedded into ChromaDB AsyncHTTPClient instance"""

    try:
        # Retrieve database collection from ChromaDB
        chroma_client = await get_chroma_client()
        collection = await chroma_client.get_collection(TEXTUAL_EMBEDDING_COLLECTION)

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
