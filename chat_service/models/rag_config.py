from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, APIError
import os
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class EnhancedQueryValidator:
    """Enhanced query validation system for Qwen2.5"""
    
    def __init__(self):
        self.validation_examples = self._get_validation_examples()
    
    def _get_validation_examples(self) -> List[Dict[str, Any]]:
        """Get comprehensive examples for query validation"""
        return [
            # PROCEED_WITH_RAG examples
            {
                "query": "What are the main findings in the quarterly report?",
                "decision": "PROCEED_WITH_RAG",
                "reason": "Specific document content request"
            },
            {
                "query": "How does the company's revenue compare to last year?",
                "decision": "PROCEED_WITH_RAG",
                "reason": "Analytical question requiring document data"
            },
            {
                "query": "List all the safety protocols mentioned in the manual",
                "decision": "PROCEED_WITH_RAG",
                "reason": "Factual extraction from specific documents"
            },
            {
                "query": "Summarize the key recommendations from the research paper",
                "decision": "PROCEED_WITH_RAG",
                "reason": "Summarization of document content"
            },
            
            # HANDLE_WITHOUT_RAG examples
            {
                "query": "What is machine learning?",
                "decision": "HANDLE_WITHOUT_RAG",
                "reason": "General knowledge question not requiring specific documents"
            },
            {
                "query": "How do I calculate compound interest?",
                "decision": "HANDLE_WITHOUT_RAG",
                "reason": "General procedural knowledge"
            },
            {
                "query": "Hello, how are you?",
                "decision": "HANDLE_WITHOUT_RAG",
                "reason": "Conversational greeting"
            },
            {
                "query": "Can you help me brainstorm ideas for a presentation?",
                "decision": "HANDLE_WITHOUT_RAG",
                "reason": "Creative assistance not requiring document search"
            },
            
            # INVALID_QUERY examples
            {
                "query": "banana",
                "decision": "INVALID_QUERY",
                "reason": "Single word without context"
            },
            {
                "query": "ajsdlkfj askdjf",
                "decision": "INVALID_QUERY",
                "reason": "Gibberish text"
            },
            {
                "query": "???",
                "decision": "INVALID_QUERY",
                "reason": "No meaningful content"
            },
            
            # NEEDS_CLARIFICATION examples
            {
                "query": "Tell me about it",
                "decision": "NEEDS_CLARIFICATION",
                "reason": "Ambiguous reference - what is 'it'?"
            },
            {
                "query": "What about the data?",
                "decision": "NEEDS_CLARIFICATION",
                "reason": "Vague reference - which data and what aspect?"
            },
            {
                "query": "More information please",
                "decision": "NEEDS_CLARIFICATION",
                "reason": "No specific topic or context provided"
            }
        ]
    
    def get_enhanced_validation_prompt(self, query: str, collection_info: Optional[str] = None) -> str:
        """Generate enhanced validation prompt with context awareness"""
        
        examples_text = "\n".join([
            f'Query: "{ex["query"]}" -> {ex["decision"]} ({ex["reason"]})'
            for ex in self.validation_examples
        ])
        
        collection_context = ""
        if collection_info:
            collection_context = f"\nCollection Context: {collection_info}"
        
        return f"""You are an intelligent query router for a document-based Q&A system using RAG (Retrieval Augmented Generation).

Your task is to analyze user queries and decide the best approach to handle them.

DECISION OPTIONS:
1. PROCEED_WITH_RAG - Query needs document search and retrieval
   - Asks for specific information from documents
   - Requires analysis of document content
   - Seeks factual data, summaries, or insights from specific sources
   
2. HANDLE_WITHOUT_RAG - Query can be answered with general knowledge
   - General knowledge questions
   - Conversational queries
   - Procedural or how-to questions not requiring specific documents
   - Greetings and casual conversation
   
3. INVALID_QUERY - Query is meaningless or too vague
   - Gibberish or random characters
   - Single words without context
   - Incomplete thoughts
   
4. NEEDS_CLARIFICATION - Query is ambiguous and needs more context
   - Vague references without clear subjects
   - Missing important context
   - Ambiguous pronouns or references

EXAMPLES:
{examples_text}{collection_context}

INSTRUCTIONS:
Analyze the query considering:
1. Specificity - Is the query specific enough to be actionable?
2. Context dependency - Does it require specific document content?
3. Intent clarity - Is the user's intent clear?
4. Scope - Is it asking for general knowledge vs. specific document information?

Respond in this exact format:
DECISION: [PROCEED_WITH_RAG|HANDLE_WITHOUT_RAG|INVALID_QUERY|NEEDS_CLARIFICATION]
CONFIDENCE: [HIGH|MEDIUM|LOW]
REASON: [Brief explanation of your decision]
SUGGESTION: [If not PROCEED_WITH_RAG, suggest how to handle or what clarification is needed]

Query: "{query}"
"""


class QueryType(Enum):
    """Enumeration of supported query types"""
    GENERAL = "general"
    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    SUMMARIZATION = "summarization"


class QwenRAGConfig:
    """Configuration class for Qwen-2.5 RAG optimization"""
    
    def __init__(self):
        self.model_name = os.getenv("OPENAI_MODEL", "qwen2.5-0.5b-instruct")
        
        # Qwen-2.5 generation parameters optimized for RAG
        self.generation_params = {
            "temperature": float(os.getenv("QWEN_TEMPERATURE", "0.1")),
            "max_tokens": int(os.getenv("QWEN_MAX_TOKENS", "2000")),
            "top_k": int(os.getenv("QWEN_TOP_K", "5")),
            "frequency_penalty": float(os.getenv("QWEN_FREQ_PENALTY", "0.1")),
            "presence_penalty": float(os.getenv("QWEN_PRESENCE_PENALTY", "0.1")),
        }
        
        # Query parameters (lighter settings for query validation and classification)
        self.validation_params = {
            "temperature": 0.0,
            "max_tokens": 500,
            "top_p": float(os.getenv("QWEN_TOP_P", "0.8")),
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }
        
        # Context management
        self.max_context_length = int(os.getenv("QWEN_MAX_CONTEXT", "4000"))
        
        # RAG-specific settings
        self.min_similarity_score = float(os.getenv("QWEN_MIN_SIMILARITY", "0.1"))
        self.enable_reranking = os.getenv("QWEN_ENABLE_RERANKING", "true").lower() == "true"

        # RAG Optimization flags
        self.enable_llm_query_classification = os.getenv("ENABLE_LLM_QUERY_CLASSIFICATION", "true").lower() == "true"
        self.enable_response_post_processing = os.getenv("ENABLE_RESPONSE_POST_PROCESSING", "true").lower() == "true"
        

class QueryClassificationExamples:
    """Few-shot examples for query type classification"""
    
    @staticmethod
    def get_classification_examples() -> List[Dict[str, str]]:
        """Returns comprehensive examples for each query type"""
        return [
            # Factual queries - seeking specific information, data, or facts
            {"query": "What is the capital of France?", "type": "factual"},
            {"query": "When was the Declaration of Independence signed?", "type": "factual"},
            {"query": "How many employees work at the company?", "type": "factual"},
            {"query": "List all the ingredients in the recipe.", "type": "factual"},
            {"query": "What are the system requirements for the software?", "type": "factual"},
            {"query": "Who is the CEO of the organization?", "type": "factual"},
            {"query": "Define machine learning.", "type": "factual"},
            {"query": "What is my shopping list?", "type": "factual"},
            {"query": "Show me the sales figures for last quarter.", "type": "factual"},
            
            # Analytical queries - requiring analysis, comparison, evaluation
            {"query": "Why did the stock price decline last month?", "type": "analytical"},
            {"query": "How does renewable energy compare to fossil fuels?", "type": "analytical"},
            {"query": "Analyze the pros and cons of remote work.", "type": "analytical"},
            {"query": "What are the implications of this policy change?", "type": "analytical"},
            {"query": "Evaluate the effectiveness of the marketing campaign.", "type": "analytical"},
            {"query": "How do these two products differ in performance?", "type": "analytical"},
            {"query": "Assess the risks associated with this investment.", "type": "analytical"},
            {"query": "What factors contributed to the project's success?", "type": "analytical"},
            {"query": "Examine the relationship between customer satisfaction and retention.", "type": "analytical"},
            
            # Summarization queries - requesting condensed overview or summary
            {"query": "Summarize the main points of the report.", "type": "summarization"},
            {"query": "Give me an overview of the quarterly results.", "type": "summarization"},
            {"query": "Summarize my shopping list.", "type": "summarization"},
            {"query": "Provide a summary of the meeting minutes.", "type": "summarization"},
            {"query": "What are the key takeaways from the research paper?", "type": "summarization"},
            {"query": "Condense the main findings of the survey.", "type": "summarization"},
            {"query": "Give me the highlights of the project status.", "type": "summarization"},
            {"query": "Summarize the customer feedback trends.", "type": "summarization"},
            {"query": "Provide an executive summary of the proposal.", "type": "summarization"},
            
            # General queries - conversational, complex, or multi-faceted
            {"query": "How can I improve my productivity?", "type": "general"},
            {"query": "Tell me about artificial intelligence.", "type": "general"},
            {"query": "What should I consider when buying a car?", "type": "general"},
            {"query": "Help me understand this concept better.", "type": "general"},
            {"query": "Can you explain how this process works?", "type": "general"},
            {"query": "What are some best practices for project management?", "type": "general"},
            {"query": "I need advice on career development.", "type": "general"},
            {"query": "How do I troubleshoot this technical issue?", "type": "general"},
            {"query": "What would you recommend for this situation?", "type": "general"},
        ]

class QwenPromptTemplates:
    """Specialized prompt templates for different types of RAG queries with Qwen-2.5"""
    
    @staticmethod
    def get_classification_prompt(query: str) -> str:
        """Generate prompt for LLM-based query classification"""
        examples = QueryClassificationExamples.get_classification_examples()
        
        # Create few-shot examples string
        examples_text = "\n".join([
            f"Query: \"{example['query']}\" -> Type: {example['type']}"
            for example in examples
        ])
        
        return f"""You are an expert at classifying user queries into specific types for optimal response generation.

Query Types:
- factual: Requests for specific information, data, facts, definitions, or lists
- analytical: Requests for analysis, comparison, evaluation, or reasoning about relationships and causes
- summarization: Requests for summaries, overviews, main points, or condensed information
- general: Conversational queries, advice-seeking, explanations, or multi-faceted questions

Examples:
{examples_text}

Instructions:
- Analyze the user's intent and primary goal
- Consider the expected response format and depth
- Classify based on what type of processing would best serve the user
- Respond with only one word: factual, analytical, summarization, or general

Query: "{query}"
Type:"""

    @staticmethod
    def get_system_prompt(query_type: str) -> str:
        """Get system prompt based on query type"""
        
        prompts = {
            QueryType.GENERAL.value: """You are Qwen, an advanced AI assistant specialized in document analysis and question answering.

Your primary responsibilities:
- Analyze the provided document context carefully
- Answer questions based ONLY on the information present in the context
- Maintain accuracy and avoid hallucination
- Provide structured, comprehensive responses
- Cite specific sections when making claims

Key principles:
- If information is not in the context, clearly state this limitation
- Use direct quotes from the context when appropriate
- Organize your response logically with clear reasoning
- Maintain professional tone while being accessible""",

            QueryType.FACTUAL.value: """You are Qwen, a precision-focused AI assistant for factual document analysis.

Your task is to extract and present factual information from documents with maximum accuracy:
- Only state facts that are explicitly mentioned in the context
- Use exact quotes when presenting specific data, numbers, or claims
- If asked about information not in the context, respond with "This information is not available in the provided document"
- Structure factual responses with clear categorization
- Distinguish between facts, opinions, and interpretations in the source
- For lists or itemized information, present them in a clear, organized format""",

            QueryType.ANALYTICAL.value: """You are Qwen, an analytical AI assistant specialized in document interpretation and analysis.

Your approach:
- Analyze the document context for patterns, themes, and key insights
- Synthesize information from multiple sections when relevant
- Provide reasoned interpretations based on the available evidence
- Highlight relationships between different parts of the document
- Distinguish between what the document states directly vs. what can be reasonably inferred
- Structure analytical responses with clear reasoning chains
- Consider multiple perspectives when the document presents them""",

            QueryType.SUMMARIZATION.value: """You are Qwen, an expert at document summarization and synthesis.

Your summarization strategy:
- Identify the main themes and key points from the context
- Organize information hierarchically (main points, supporting details)
- Preserve important nuances and qualifications
- Maintain the original document's tone and perspective
- Create coherent summaries that capture essential information
- Use bullet points or structured format when appropriate for clarity
- Ensure summaries are concise yet comprehensive"""
        }
        
        return prompts.get(query_type, prompts[QueryType.GENERAL.value])
    
    @staticmethod
    def format_user_prompt(question: str, context: str, query_type: str) -> str:
        """Format user prompt with context and question"""
        
        prompt_formats = {
            QueryType.FACTUAL.value: f"""**DOCUMENT CONTEXT:**
{context}

**FACTUAL QUERY:** {question}

**INSTRUCTIONS:** Extract and present only the factual information from the document that directly answers this question. Use exact quotes where appropriate and clearly indicate if the requested information is not available.""",

            QueryType.ANALYTICAL.value: f"""**DOCUMENT CONTEXT:**
{context}

**ANALYTICAL QUERY:** {question}

**INSTRUCTIONS:** Analyze the document context to provide a comprehensive answer. Consider relationships between different parts of the document and provide reasoned interpretations based on the evidence presented.""",

            QueryType.SUMMARIZATION.value: f"""**DOCUMENT CONTEXT:**
{context}

**SUMMARIZATION REQUEST:** {question}

**INSTRUCTIONS:** Create a well-structured summary addressing the request. Organize the information logically and maintain the document's key insights and perspective.""",

            QueryType.GENERAL.value: f"""**DOCUMENT CONTEXT:**
{context}

**QUESTION:** {question}

**INSTRUCTIONS:** Based on the document context provided above, give a comprehensive and accurate answer to the question. If the context doesn't contain sufficient information, clearly explain what information is missing."""
        }
        
        return prompt_formats.get(query_type, prompt_formats[QueryType.GENERAL.value])

class QwenRAGOptimizer:
    """Advanced optimization techniques for Qwen-2.5 RAG"""
    
    @staticmethod
    async def classify_query_with_llm(
        question: str, 
        model_name: str,
        classification_params: Dict[str, Any],
        openai_client: AsyncOpenAI
    ) -> str:
        """Use LLM to classify query type with few-shot examples"""
        try:
            classification_prompt = QwenPromptTemplates.get_classification_prompt(question)
            
            messages = [
                {
                    "role": "user",
                    "content": classification_prompt
                }
            ]
            
            response = await openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                **classification_params
            )
            
            if response.choices and response.choices[0].message.content:
                predicted_type = response.choices[0].message.content.strip().lower()
                
                # Validate the predicted type
                valid_types = [qt.value for qt in QueryType]
                if predicted_type in valid_types:
                    logger.info(f"LLM classified query as: {predicted_type}")
                    return predicted_type
                else:
                    logger.warning(f"LLM returned invalid query type: {predicted_type}")
                    return QueryType.GENERAL.value
            else:
                logger.error("LLM classification returned empty response")
                return QueryType.GENERAL.value
                
        except APIError as e:
            logger.error(f"LLM query classification failed: {e}")
            return QueryType.GENERAL.value

    
    @staticmethod
    async def detect_query_type(
        question: str, 
        openai_client: AsyncOpenAI,
        model_name: str,
        config: QwenRAGConfig,
    ) -> str:
        """
        Detect query type using LLM classification
        """
        # Try LLM-based classification if enabled and client is available
        if (config and config.enable_llm_query_classification and 
            openai_client and model_name):
            
            llm_classification = await QwenRAGOptimizer.classify_query_with_llm(
                question, model_name, config.validation_params, openai_client
            )
            
            # If LLM classification succeeded, return it
            if llm_classification != QueryType.GENERAL.value:
                return llm_classification
        
        # If LLM classification failed, return General
        return QueryType.GENERAL.value
    
    @staticmethod
    def optimize_chunks_for_qwen(chunks: List[Dict[str, Any]], max_context_length: int = 4000) -> tuple[List[Dict[str, Any]], str]:
        """Optimize chunk selection and formatting specifically for Qwen-2.5"""
        
        if not chunks:
            return [], ""
        
        # Build context with length management
        selected_chunks = []
        context_parts = []
        current_length = 0
        
        for i, chunk in enumerate(chunks):
            content = chunk.get('content', '')
            
            # Format chunk for Qwen-2.5
            chunk_header = f"--- Document Section {i+1} (Relevance: {chunk.get('similarity_score', 0):.2f}) ---"
            formatted_chunk = f"{chunk_header}\n{content}\n"
            
            # Check length constraints
            chunk_length = len(formatted_chunk)
            if current_length + chunk_length > max_context_length:
                break
            
            selected_chunks.append(chunk)
            context_parts.append(formatted_chunk)
            current_length += chunk_length
        
        return selected_chunks, "\n".join(context_parts)
    
    @staticmethod
    def post_process_qwen_response(response: str) -> str:
        """Post-process Qwen-2.5 response for better formatting"""
        
        # Remove any potential repetition
        lines = response.split('\n')
        seen_lines = set()
        filtered_lines = []
        
        for line in lines:
            line_clean = line.strip()
            if line_clean and line_clean not in seen_lines:
                seen_lines.add(line_clean)
                filtered_lines.append(line)
            elif not line_clean:  # Keep empty lines for formatting
                filtered_lines.append(line)
        
        cleaned_response = '\n'.join(filtered_lines)
        
        # Ensure response ends properly
        if cleaned_response and not cleaned_response.rstrip().endswith(('.', '!', '?', ':')):
            cleaned_response = cleaned_response.rstrip() + '.'
        
        return cleaned_response.strip()
    