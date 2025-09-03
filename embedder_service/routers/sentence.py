# For data chunking and embedding

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import logging
import uuid

from models.embed import DataRequest
from shared_utils.chroma_client import get_chroma_client
from shared_utils.s3_utils import save_job, load_job
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
    segment_start_idx = []
    segment_end_idx = []

    sentences = sent_tokenize(text)
    if not sentences:
        return [], [], []

    last_match_end = 0
    current_segment_start = 0

    for sentence in sentences:
        new_word_count = len(sentence.split())

        try:
            sentence_start = text.index(sentence, last_match_end)
        except ValueError as e:
            # if sentences can't be located raise an error, as the tokenizer should not modify the text.
            logger.error(f"Failed to locate sentence {{{sentence}}} in orignal text.\n{e}")
            raise HTTPException(status_code=500, detail="Embedder failure.")

        if word_count > 0 and word_count + new_word_count > max_length:
            segments.append(" ".join(current_segment_sentences))
            segment_start_idx.append(current_segment_start)
            segment_end_idx.append(last_match_end)

            current_segment_sentences = []
            word_count = 0
            current_segment_start = sentence_start

        current_segment_sentences.append(sentence.strip())
        word_count += new_word_count
        last_match_end = sentence_start + len(sentence)

    # Add the final segment
    if current_segment_sentences:
        segments.append(" ".join(current_segment_sentences))
        segment_start_idx.append(current_segment_start)
        segment_end_idx.append(last_match_end)

    return segments, segment_start_idx, segment_end_idx


async def token_data_chunking(request: DataRequest) -> List[Dict[str, Any]]:
    """Perform chunking / splitting of data via sentences,
    and reject by returning empty list if PDF document has no textual content"""

    logger.info("Starting chunking process...")

    try:
        if not request.text.strip():
            raise HTTPException(
                status_code=400, detail="No textual content found in PDF"
            )

        chunks, chunk_start_idx, chunk_end_idx = split_in_segments_by_sentences(request.text, MAX_STRING_LENGTH)
        logger.info(f"Number of chunks: {len(chunks)}")

        chunk_data = []

        for chunk, chunk_start, chunk_end in zip(chunks, chunk_start_idx, chunk_end_idx):
            # First iteration: Extract first chunk of doc.page_content
            chunk_content = chunk
            logger.info(f"Length of chunk: {len(chunk_content.strip())}")

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

        logger.info(chunk_data)
        return chunk_data
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        raise HTTPException(status_code=500, detail="Chunking failed.")


async def process_sentence_embedding(request: DataRequest):
    """Background task to process sentence embedding"""
    try:
        # Extracted data has to be chunked up first
        chunk_data = await token_data_chunking(request)

        if not chunk_data:
            error_job = {
                "doc_id": request.doc_id,
                "status": "error",
                "message": "No chunks were created from the input text"
            }
            save_job(
                doc_id=request.doc_id,
                job_data=error_job,
                status="failed",
                job_type="sentence_embedding"
            )
            return

        # Once chunking is done, embed into ChromaDB with the specified embedding model
        embed_results = await vectorize_chromadb(chunk_data, request.config, TEXTUAL_EMBEDDING_COLLECTION)

        result_data = {
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
        
        save_job(
            doc_id=request.doc_id,
            job_data=result_data,
            status="completed",
            job_type="sentence_embedding"
        )
        
    except Exception as e:
        logger.error(f"Sentence embedding failed: {e}")
        error_job = {
            "doc_id": request.doc_id,
            "status": "error",
            "message": f"Sentence embedding failed: {str(e)}"
        }
        save_job(
            doc_id=request.doc_id,
            job_data=error_job,
            status="failed",
            job_type="sentence_embedding"
        )


@router.post("/", status_code=202)
async def submit_sentence_embedding(request: DataRequest, background_tasks: BackgroundTasks):
    """Submit a document for sentence embedding processing"""
    save_job(
        doc_id=request.doc_id,
        job_data={},
        status="processing",
        job_type="sentence_embedding"
    )

    background_tasks.add_task(process_sentence_embedding, request)
    return {"doc_id": request.doc_id, "status": "processing"}


@router.get("/{doc_id}")
async def get_sentence_embedding_status(doc_id: str):
    """Get the status and results of sentence embedding processing"""
    job = load_job(doc_id=doc_id, job_type="sentence_embedding")
    if not job:
        raise HTTPException(status_code=404, detail="Document ID not found")

    if job.get("status") == "failed":
        error_message = job.get("data", {}).get("message", "Processing failed")
        raise HTTPException(status_code=500, detail=error_message)
    
    job_data = job.get("data", {})
    
    return {
        "doc_id": doc_id,
        "status": job.get("status", "unknown"),
        "result": job_data if job.get("status") == "completed" else None
    }


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
