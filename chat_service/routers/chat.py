from fastapi import APIRouter, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from openai import OpenAI, APIError
from typing import List, Dict, Any, Optional
from shared_utils.openai_client import get_openai_client
from shared_utils.chroma_client import get_chroma_client
import logging
from models.chat import ChatRequest, ChatResponse
from models.rag_config import QwenRAGConfig, QwenPromptTemplates, QwenRAGOptimizer

router = APIRouter(prefix="/chat")

logger = logging.getLogger(__name__)

# Initialize Qwen-2.5 RAG configuration
qwen_config = QwenRAGConfig()
prompt_templates = QwenPromptTemplates()
qwen_optimizer = QwenRAGOptimizer()

OPENAI_MODEL_NAME = qwen_config.model_name


def prepare_retrieval_results(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert ChromaDB results to structured chunks for RAG using OPENAI_MODEL"""
    chunks = []
    
    if not results or not results.get('documents'):
        return chunks
    
    # Get the first (and typically only) query results
    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]
    ids = results.get('ids', [[]])[0]
    
    for i, doc in enumerate(documents):
        chunk = {
            'content': doc,
            'chunk_id': ids[i] if i < len(ids) else f"chunk_{i}",
            'similarity_score': 1 - distances[i] if i < len(distances) else 0.0,  # Convert distance to similarity
            'metadata': metadatas[i] if i < len(metadatas) else {},
            'doc_id': metadatas[i].get('doc_id') if i < len(metadatas) and metadatas[i] else None  # Extract doc_id from metadata
        }
        chunks.append(chunk)
    
    # Filter chunks by minimum similarity if configured
    if qwen_config.min_similarity_score > 0:
        chunks = [chunk for chunk in chunks if chunk['similarity_score'] >= qwen_config.min_similarity_score]
    
    return chunks


def rerank_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simple reranking based on document diversity and relevance
    """
    # Group chunks by doc_id
    doc_chunks = {}
    for chunk in chunks:
        doc_id = chunk.get('doc_id', 'unknown')
        if doc_id not in doc_chunks:
            doc_chunks[doc_id] = []
        doc_chunks[doc_id].append(chunk)
    
    # Sort chunks within each doc_id by similarity score
    for doc_id in doc_chunks:
        doc_chunks[doc_id].sort(key=lambda x: x['similarity_score'], reverse=True)
    
    reranked_chunks = []
    
    # Determine the number of rounds based on the document with the most chunks
    if doc_chunks:
        max_depth = max(len(chunks) for chunks in doc_chunks.values())
    else:
        max_depth = 0

    # Interleave by taking one chunk from each document per round to ensure diversity of sources
    for i in range(max_depth):
        for doc_id in doc_chunks:
            if i < len(doc_chunks[doc_id]):
                reranked_chunks.append(doc_chunks[doc_id][i])
    
    logger.info(f"Reranked {len(chunks)} chunks from {len(doc_chunks)} documents")
    return reranked_chunks


async def perform_rag_query(
    query: str, 
    collection_name: str, 
    doc_id: Optional[str] = None,
    top_k: int = 5,
    query_type: str = "general",
    enable_reranking: bool = True
) -> tuple[str, List[Dict[str, Any]], str]:
    """
    Perform complete RAG query: retrieve relevant chunks and generate response
    """
    try:
        chroma_client = await get_chroma_client()
        # Step 1: Retrieve relevant chunks from ChromaDB
        collection = await chroma_client.get_collection(collection_name)
        
        query_params = {
            "query_texts": [query],
            "n_results": top_k,
            "include": ["distances", "documents", "metadatas", "embeddings"]
        }

        if doc_id:
            query_params["where"] = {"doc_id": doc_id}
            logger.info(f"Filtering results to document ID: {doc_id}")
        else:
            logger.info("Searching across all documents in collection")

        results = await collection.query(**query_params)
        
        # Step 2: Process retrieval results
        chunks = prepare_retrieval_results(results)
        
        if not chunks:
            logger.warning(f"No relevant chunks found for query: {query}")
            return "I couldn't find any relevant information in the document collection to answer your question.", [], ""
        
        # Step 3: Rerank chunks for more diverse results across multiple documents
        if enable_reranking and len(chunks) > 1:
            chunks = await rerank_chunks(chunks)
        
        # Step 4: Optimize chunks for Qwen-2.5
        optimized_chunks, context = qwen_optimizer.optimize_chunks_for_qwen(
            chunks, 
            max_context_length=qwen_config.max_context_length
        )

        num_of_docs = len(set(chunk.get('doc_id') for chunk in optimized_chunks if chunk.get('doc_id')))
        logger.info(f"Relevant chunks from {num_of_docs} documents")
        logger.info(f"Using {len(optimized_chunks)} chunks for context (total length: {len(context)} chars)")

        # Step 5: Auto-detect query type if not provided
        logger.info(f"Query type: {query_type}")
        if qwen_config.enable_query_type_detection and query_type == "general":
                query_type = qwen_optimizer.detect_query_type(query)
                logger.info(f"Auto-detected query type: {query_type}")
        
        # Step 6: Prepare system and user prompts
        system_prompt = prompt_templates.get_system_prompt(query_type)
        user_prompt = prompt_templates.format_user_prompt(query, context, query_type)
        logger.info(f"System prompt: {system_prompt}")
        logger.info(f"User prompt: {user_prompt}")

        return user_prompt, optimized_chunks, system_prompt
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail="RAG query failed")


@router.post("/", status_code=201, response_model=ChatResponse)
async def handle_chat(
    chat_request: ChatRequest,
    client: OpenAI = Depends(get_openai_client),
):
    """
    Handle incoming chat requests and return AI responses.
    """
    try:
        logger.info(chat_request.collection_name)

        # Perform RAG query to get context and relevant chunks
        user_prompt, relevant_chunks, system_prompt = await perform_rag_query(
            query=chat_request.message,
            collection_name=chat_request.collection_name,
            doc_id=chat_request.doc_id,
            top_k=chat_request.top_k,
            query_type=chat_request.query_type or "general",
            enable_reranking=qwen_config.enable_reranking
        )
        
        # Prepare messages for Qwen-2.5
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": user_prompt
            }
        ]

        response = await run_in_threadpool(
            client.chat.completions.create,
            model=OPENAI_MODEL_NAME,
            messages=messages,
            **qwen_config.generation_params,
        )
    except APIError as e:
        logger.error(f"Unexpected error during chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during chat completion")

    if not response.choices:
        logger.error("No choices found in OpenAI response: %s", response)
        raise HTTPException(
            status_code=500,
            detail="No choices found in OpenAI response",
        )

    first_choice = response.choices[0]
    if not first_choice.message or first_choice.message.content is None:
        logger.error("Malformed choice in OpenAI response: %s", first_choice)
        raise HTTPException(
            status_code=500,
            detail="Malformed choice in OpenAI response",
        )
    
    # Post-process the response
    if qwen_config.enable_response_post_processing:
        processed_response = qwen_optimizer.post_process_qwen_response(first_choice.message.content)
    else:
        processed_response = first_choice.message.content

    # Analyze document diversity in results
    doc_ids = set(chunk.get('doc_id') for chunk in relevant_chunks if chunk.get('doc_id'))
    
    # Prepare metadata for response
    metadata = {
        "query_type": chat_request.query_type,
        "chunks_used": len(relevant_chunks),
        "documents_searched_count": len(doc_ids) if doc_ids else 0,
        "document_ids": list(doc_ids) if doc_ids else [],
        "total_context_length": len(user_prompt),
        "model_used": OPENAI_MODEL_NAME,
        "collection_name": chat_request.collection_name,
        "generation_params": qwen_config.generation_params,
        "reranking_enabled": qwen_config.enable_reranking
    }
    
    # Return structured response
    return ChatResponse(
        response=processed_response,
        relevant_chunks=relevant_chunks,
        metadata=metadata
    )
