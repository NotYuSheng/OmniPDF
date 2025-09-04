from typing import List, Dict
import os
import logging
from enum import Enum

logger = logging.getLogger(__name__)


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
            "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.1")),
            "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", "2000")),
            "top_p": float(os.getenv("MODEL_TOP_P", "0.8")),
            "frequency_penalty": float(os.getenv("MODEL_FREQ_PENALTY", "0.1")),
            "presence_penalty": float(os.getenv("MODEL_PRESENCE_PENALTY", "0.1")),
        }

        # Query classification parameters (lighter settings for classification)
        self.classification_params = {
            "temperature": 0.0,  # Deterministic classification
            "max_tokens": 50,  # Short response needed
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

        # HyDE-specific generation parameters
        self.hyde_generation_params = {
            "temperature": 0.0,
            "max_tokens": 200,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

        # Context management
        self.max_context_length = int(os.getenv("MODEL_MAX_CONTEXT", "4000"))

        # RAG-specific settings
        self.min_similarity_score = float(os.getenv("MODEL_MIN_SIMILARITY", "0.1"))
        self.enable_reranking = (
            os.getenv("MODEL_ENABLE_RERANKING", "true").lower() == "true"
        )

        # RAG Optimization flags
        self.enable_llm_query_classification = (
            os.getenv("ENABLE_LLM_QUERY_CLASSIFICATION", "true").lower() == "true"
        )
        self.enable_response_post_processing = (
            os.getenv("ENABLE_RESPONSE_POST_PROCESSING", "true").lower() == "true"
        )
        self.enable_hyde = os.getenv("ENABLE_HYDE", "true").lower() == "true"

        # Fallback to keyword-based classification if LLM classification fails
        self.fallback_to_keyword_classification = (
            os.getenv("FALLBACK_TO_KEYWORD_CLASSIFICATION", "true").lower() == "true"
        )


class QueryClassificationExamples:
    """Few-shot examples for query type classification"""

    @staticmethod
    def get_classification_examples() -> List[Dict[str, str]]:
        """Returns comprehensive examples for each query type"""
        return [
            # Factual queries - seeking specific information, data, or facts
            {
                "query": "What is the capital of France?",
                "type": "factual"
            },
            {
                "query": "When was the Declaration of Independence signed?",
                "type": "factual",
            },
            {
                "query": "How many employees work at the company?",
                "type": "factual"
            },
            {
                "query": "List all the ingredients in the recipe.",
                "type": "factual"
            },
            {
                "query": "What are the system requirements for the software?",
                "type": "factual",
            },
            {
                "query": "Who is the CEO of the organization?",
                "type": "factual"
            },
            {
                "query": "Define machine learning.",
                "type": "factual"
            },
            {
                "query": "What is my shopping list?",
                "type": "factual"
            },
            {
                "query": "Show me the sales figures for last quarter.",
                "type": "factual"
            },
            # Analytical queries - requiring analysis, comparison, evaluation
            {
                "query": "Why did the stock price decline last month?",
                "type": "analytical",
            },
            {
                "query": "How does renewable energy compare to fossil fuels?",
                "type": "analytical",
            },
            {
                "query": "Analyze the pros and cons of remote work.",
                "type": "analytical",
            },
            {
                "query": "What are the implications of this policy change?",
                "type": "analytical",
            },
            {
                "query": "Evaluate the effectiveness of the marketing campaign.",
                "type": "analytical",
            },
            {
                "query": "How do these two products differ in performance?",
                "type": "analytical",
            },
            {
                "query": "Assess the risks associated with this investment.",
                "type": "analytical",
            },
            {
                "query": "What factors contributed to the project's success?",
                "type": "analytical",
            },
            {
                "query": "Examine the relationship between customer satisfaction and retention.",
                "type": "analytical",
            },
            # Summarization queries - requesting condensed overview or summary
            {
                "query": "Summarize the main points of the report.",
                "type": "summarization",
            },
            {
                "query": "Give me an overview of the quarterly results.",
                "type": "summarization",
            },
            {
                "query": "Summarize my shopping list.",
                "type": "summarization"
            },
            {
                "query": "Provide a summary of the meeting minutes.",
                "type": "summarization",
            },
            {
                "query": "What are the key takeaways from the research paper?",
                "type": "summarization",
            },
            {
                "query": "Condense the main findings of the survey.",
                "type": "summarization",
            },
            {
                "query": "Give me the highlights of the project status.",
                "type": "summarization",
            },
            {
                "query": "Summarize the customer feedback trends.",
                "type": "summarization",
            },
            {
                "query": "Provide an executive summary of the proposal.",
                "type": "summarization",
            },
            # General queries - conversational, complex, or multi-faceted
            {
                "query": "How can I improve my productivity?",
                "type": "general"
            },
            {
                "query": "Tell me about artificial intelligence.",
                "type": "general"
            },
            {
                "query": "What should I consider when buying a car?",
                "type": "general"
            },
            {
                "query": "Help me understand this concept better.",
                "type": "general"
            },
            {
                "query": "Can you explain how this process works?",
                "type": "general"
            },
            {
                "query": "What are some best practices for project management?",
                "type": "general",
            },
            {
                "query": "I need advice on career development.",
                "type": "general"
            },
            {
                "query": "How do I troubleshoot this technical issue?",
                "type": "general"
            },
            {
                "query": "What would you recommend for this situation?",
                "type": "general",
            },
        ]


class QwenPromptTemplates:
    """Specialized prompt templates for different types of RAG queries with Qwen-2.5"""

    @staticmethod
    def get_classification_prompt(query: str) -> str:
        """Generate prompt for LLM-based query classification"""
        examples = QueryClassificationExamples.get_classification_examples()

        # Create few-shot examples string
        examples_text = "\n".join(
            [
                f'Query: "{example["query"]}" -> Type: {example["type"]}'
                for example in examples
            ]
        )

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
- Ensure summaries are concise yet comprehensive""",
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

**INSTRUCTIONS:** Based on the document context provided above, give a comprehensive and accurate answer to the question. If the context doesn't contain sufficient information, clearly explain what information is missing.""",
        }

        return prompt_formats.get(query_type, prompt_formats[QueryType.GENERAL.value])

    @staticmethod
    def get_hyde_prompt(question: str) -> str:
        """Generate prompt for HyDE document generation"""
        return f"""You are an expert in document retrieval and analysis. Your task is to generate a hypothetical document that fully answers the user's question.

Instructions:
- Write a comprehensive, self-contained document that provides a complete answer to the query below.
- The document should be well-structured, detailed, and cover all aspects of the question.
- Do not include any preamble or introductory phrases like "Here is a hypothetical document."
- The goal is to create a document that, if it existed, would be the perfect source to answer the user's question.

Query: "{question}"

Hypothetical Document:"""
