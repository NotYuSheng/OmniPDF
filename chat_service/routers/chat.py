from fastapi import APIRouter, HTTPException, Depends
from openai import AsyncOpenAI, APIError
from typing import List, Dict, Any, Optional
from shared_utils.openai_client import get_openai_client
from shared_utils.chroma_client import get_chroma_client
import logging
from models.chat import ChatRequest, ChatResponse
from models.rag_config import QwenRAGConfig, QwenPromptTemplates, QwenRAGOptimizer, QueryType, EnhancedQueryValidator

router = APIRouter(prefix="/chat")

logger = logging.getLogger(__name__)

# Initialize Qwen-2.5 RAG configuration
qwen_config = QwenRAGConfig()
prompt_templates = QwenPromptTemplates()
qwen_optimizer = QwenRAGOptimizer()
query_validator = EnhancedQueryValidator()

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


async def rerank_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simple reranking based on document diversity and relevance
    """
    # Group chunks by doc_id
    doc_chunks = {}
    for chunk in chunks:
        doc_id = chunk.get('doc_id')
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
    top_k: int,
    doc_id: Optional[str] = None,
    enable_reranking: bool = True,
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
            return ("I couldn't find any relevant information in the document collection to answer your question.", 
                   [], "", QueryType.GENERAL.value)
        
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

        # Step 5: Enhanced query type detection
        detected_query_type = await qwen_optimizer.detect_query_type(
            question=query,
            model_name=OPENAI_MODEL_NAME,
            config=qwen_config,
            openai_client=openai_client
        )
        logger.info(f"Auto-detected query type: {detected_query_type}")
        
        # Step 6: Prepare system and user prompts
        system_prompt = prompt_templates.get_system_prompt(detected_query_type)
        user_prompt = prompt_templates.format_user_prompt(query, context, detected_query_type)
        
        logger.info(f"Final query type: {detected_query_type}")
        logger.debug(f"System prompt length: {len(system_prompt)} chars")
        logger.debug(f"User prompt length: {len(user_prompt)} chars")

        return user_prompt, optimized_chunks, system_prompt, detected_query_type
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail="RAG query failed")


async def validate_query_with_llm(
    query: str,
    collection_name: str,
    openai_client: AsyncOpenAI = None,
    model_name: str = OPENAI_MODEL_NAME,
) -> tuple[bool, Optional[str]]:
    """
    Use LLM to validate if query is meaningful and can be answered with documents.
    """
    collection_info = ""
    
    if collection_name:
        # List out all documents in ChromaDB collection
        # collection_info = f"Available documents in {collection_name}:\n{filename}: {exec_summary}" 
        collection_info=f"{collection_name} collection in ChromaDB."
        logger.info(collection_info)
        
    validation_prompt = query_validator._get_enhanced_validation_prompt(query, collection_info)

    try:
        # Prepare messages for Qwen-2.5
        messages = [
            {
                "role": "system",
                "content": "You are an expert query analysis system. Follow the instructions precisely and provide structured responses."
            },
            {
                "role": "user",
                "content": validation_prompt
            }
        ]

        response = await openai_client.chat.completions.create(
            model=model_name,
            messages=messages,
            **qwen_config.validation_params
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"Result: {result}")
        decision_line = next((line for line in result.split('\n') if line.startswith("DECISION:")), "")
        
        if "PROCEED_WITH_RAG" in decision_line:
            return True, None

        return False, result
            
    except APIError as e:
        logger.warning(f"LLM validation failed: {e}")
        raise HTTPException(status_code=500, detail="LLM validation failed")


@router.post("/", status_code=201, response_model=ChatResponse)
async def handle_chat(
    chat_request: ChatRequest,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    """
    Handle incoming chat requests and return AI responses with enhanced query classification.
    """
    try:        
        logger.info(f"Processing chat request for collection: {chat_request.collection_name}")
        logger.info(f"User query: {chat_request.message}")

        # Simple logic to call RAG if needed
        should_rag, validation_error = await validate_query_with_llm(
            chat_request.message,
            chat_request.collection_name, 
            client, 
            OPENAI_MODEL_NAME
        )
        
        # Do not perform RAG if user query is invalid
        if not should_rag:
            logger.info("LLM query validation failed")
            metadata_without_rag = {
                "query_type": "invalid",
                "chunks_used": 0,
                "documents_searched_count": 0,
                "document_ids": [],
                "total_context_length": 0,
                "model_used": OPENAI_MODEL_NAME,
                "collection_name": chat_request.collection_name,
                "rag_performed": False
            }

            return ChatResponse(
                response=f"""I'm sorry, but I couldn't process your query based on the documents in {chat_request.collection_name} that you want to query data from. {validation_error} Please provide a clear, specific question that I can help answer using the available documents in {chat_request.collection_name}.""",
                relevant_chunks=[],
                metadata=metadata_without_rag
            )
        else:
            # Perform RAG query with enhanced classification if user query is valid
            user_prompt, relevant_chunks, system_prompt, detected_query_type = await perform_rag_query(
                openai_client=client,
                query=chat_request.message,
                collection_name=chat_request.collection_name,
                doc_id=chat_request.doc_id,
                top_k=qwen_config.generation_params["top_k"],
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
