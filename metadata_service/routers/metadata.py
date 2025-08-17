from fastapi import APIRouter, HTTPException, Depends
from openai import AsyncOpenAI, APIError
from typing import List, Dict, Any, Optional
from shared_utils.openai_client import get_openai_client
from shared_utils.chroma_client import get_chroma_client
import logging
import os
from metadata_service.models.metadata import MetadataRequest, ChatResponse
from models.rag_config import QwenRAGConfig, QwenPromptTemplates, QwenRAGOptimizer, QueryType, EnhancedQueryValidator

router = APIRouter(prefix="/chat")

logger = logging.getLogger(__name__)

# Initialize Qwen-2.5 RAG configuration
qwen_config = QwenRAGConfig()
prompt_templates = QwenPromptTemplates()
qwen_optimizer = QwenRAGOptimizer()
query_validator = EnhancedQueryValidator()

OPENAI_MODEL_NAME = qwen_config.model_name
QWEN_TOP_K = int(os.getenv("QWEN_TOP_K"))


async def perform_rag_query(
    query: str, 
    collection_name: str, 
    doc_id: Optional[str] = None,
    openai_client: AsyncOpenAI = None
) -> tuple[str, List[Dict[str, Any]], str, str]:
    """
    Perform complete RAG query: retrieve relevant chunks and generate response
    Returns: (user_prompt, optimized_chunks, system_prompt, detected_query_type)
    """
    try:
        chroma_client = await get_chroma_client()
        # Step 1: Retrieve relevant chunks from ChromaDB
        collection = await chroma_client.get_collection(collection_name)

        results = await collection.get(where={"doc_id": doc_id})
        
        # Step 2: Process retrieval results
        chunks = results.get('documents',[])
        # chunks = prepare_retrieval_results(results)
        
        if not chunks:
            logger.warning(f"No relevant chunks found for query: {query}")
            return ("I couldn't find any relevant information in the document collection to answer your question.", 
                   [], "", QueryType.GENERAL.value)
        
        # Step 4: Optimize chunks for Qwen-2.5
        optimized_chunks, context = qwen_optimizer.optimize_chunks_for_qwen(
            chunks, 
            max_context_length=qwen_config.max_context_length
        )

        return optimized_chunks
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail="RAG query failed")



@router.post("/", status_code=201, response_model=ChatResponse)
async def handle_chat(
    chat_request: MetadataRequest,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    """
    Handle incoming chat requests and return AI responses with enhanced query classification.
    """
    try:        
        logger.info(f"Processing chat request for collection: {chat_request.collection_name}")
        logger.info(f"User query: {chat_request.message}")

            # Perform RAG query with enhanced classification if user query is valid
        user_prompt, relevant_chunks, system_prompt, detected_query_type = await perform_rag_query(
            openai_client=client,
            query=chat_request.message,
            collection_name=chat_request.collection_name,
            doc_id=chat_request.doc_id,
            top_k=QWEN_TOP_K,
            enable_reranking=qwen_config.enable_reranking,
        )

        metadata_with_rag = {
            "query_type": detected_query_type,
            "chunks_used": len(relevant_chunks),
            "documents_searched_count": 0,
            "document_ids": [],
            "total_context_length": len(user_prompt) if user_prompt else 0,
            "model_used": OPENAI_MODEL_NAME,
            "collection_name": chat_request.collection_name,
            "rag_performed": True
        }

        if relevant_chunks:
            # Analyze document diversity in results if relevant chunks are found
            doc_ids = set(chunk.get('doc_id') for chunk in relevant_chunks if chunk.get('doc_id'))
            metadata_with_rag["documents_searched_count"] = len(doc_ids)
            metadata_with_rag["document_ids"] = list(doc_ids)
        
        else:
            logger.error("No relevant chunks found!")
            return ChatResponse(
                response=user_prompt,
                relevant_chunks=[],
                metadata=metadata_with_rag
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

        logger.info(f"Sending request to {OPENAI_MODEL_NAME} with {len(messages)} messages")
        response = await client.chat.completions.create(
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
    
    logger.info(f"Generated response with {len(processed_response)} characters")
    logger.info(f"Final metadata: {metadata_with_rag}")
    
    # Return structured ChatResponse if relevant chunks are found
    return ChatResponse(
        response=processed_response,
        relevant_chunks=relevant_chunks,
        metadata=metadata_with_rag
    )
