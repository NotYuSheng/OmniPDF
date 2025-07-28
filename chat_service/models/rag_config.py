import os

FACTUAL_KEYWORDS = ['what is', 'when did', 'where is', 'who is', 'how many', 'list', 'define']
ANALYTICAL_KEYWORDS = ['why', 'how does', 'analyze', 'compare', 'evaluate', 'assess', 'examine']
SUMMARY_KEYWORDS = ['summarize', 'summary', 'overview', 'main points', 'key findings']

class QwenRAGConfig:
    """Configuration class for Qwen-2.5 RAG optimization"""
    
    def __init__(self):
        self.model_name = os.getenv("QWEN_MODEL", "qwen2.5-0.5b-instruct")
        
        # Qwen-2.5 generation parameters optimized for RAG
        self.generation_params = {
            "temperature": float(os.getenv("QWEN_TEMPERATURE", "0.1")),
            "max_tokens": int(os.getenv("QWEN_MAX_TOKENS", "2000")),
            "top_p": float(os.getenv("QWEN_TOP_P", "0.8")),
            "frequency_penalty": float(os.getenv("QWEN_FREQ_PENALTY", "0.1")),
            "presence_penalty": float(os.getenv("QWEN_PRESENCE_PENALTY", "0.1")),
        }
        
        # Context management
        self.max_context_length = int(os.getenv("QWEN_MAX_CONTEXT", "4000"))
        
        # RAG-specific settings
        self.min_similarity_score = float(os.getenv("QWEN_MIN_SIMILARITY", "0.1"))
        self.enable_reranking = os.getenv("QWEN_ENABLE_RERANKING", "true").lower() == "true"

        # RAG Optimization flags
        self.enable_query_type_detection = os.getenv("ENABLE_QUERY_TYPE_DETECTION", "true").lower() == "true"
        self.enable_response_post_processing = os.getenv("ENABLE_RESPONSE_POST_PROCESSING", "true").lower() == "true"

class QwenPromptTemplates:
    """Specialized prompt templates for different types of RAG queries with Qwen-2.5"""
    
    @staticmethod
    def get_system_prompt(query_type: str) -> str:
        """Get system prompt based on query type"""
        
        prompts = {
            "general": """You are Qwen, an advanced AI assistant specialized in document analysis and question answering.

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

            "factual": """You are Qwen, a precision-focused AI assistant for factual document analysis.

Your task is to extract and present factual information from documents with maximum accuracy:
- Only state facts that are explicitly mentioned in the context
- Use exact quotes when presenting specific data, numbers, or claims
- If asked about information not in the context, respond with "This information is not available in the provided document"
- Structure factual responses with clear categorization
- Distinguish between facts, opinions, and interpretations in the source""",

            "analytical": """You are Qwen, an analytical AI assistant specialized in document interpretation and analysis.

Your approach:
- Analyze the document context for patterns, themes, and key insights
- Synthesize information from multiple sections when relevant
- Provide reasoned interpretations based on the available evidence
- Highlight relationships between different parts of the document
- Distinguish between what the document states directly vs. what can be reasonably inferred
- Structure analytical responses with clear reasoning chains""",

            "summarization": """You are Qwen, an expert at document summarization and synthesis.

Your summarization strategy:
- Identify the main themes and key points from the context
- Organize information hierarchically (main points, supporting details)
- Preserve important nuances and qualifications
- Maintain the original document's tone and perspective
- Create coherent summaries that capture essential information
- Use bullet points or structured format when appropriate for clarity"""
        }
        
        return prompts.get(query_type, prompts["general"])
    
    @staticmethod
    def format_user_prompt(question: str, context: str, query_type: str) -> str:
        """Format user prompt with context and question"""
        
        if query_type == "factual":
            return f"""**DOCUMENT CONTEXT:**
{context}

**FACTUAL QUERY:** {question}

**INSTRUCTIONS:** Extract and present only the factual information from the document that directly answers this question. Use exact quotes where appropriate and clearly indicate if the requested information is not available."""

        elif query_type == "analytical":
            return f"""**DOCUMENT CONTEXT:**
{context}

**ANALYTICAL QUERY:** {question}

**INSTRUCTIONS:** Analyze the document context to provide a comprehensive answer. Consider relationships between different parts of the document and provide reasoned interpretations based on the evidence presented."""

        elif query_type == "summarization":
            return f"""**DOCUMENT CONTEXT:**
{context}

**SUMMARIZATION REQUEST:** {question}

**INSTRUCTIONS:** Create a well-structured summary addressing the request. Organize the information logically and maintain the document's key insights and perspective."""

        else:  # general
            return f"""**DOCUMENT CONTEXT:**
{context}

**QUESTION:** {question}

**INSTRUCTIONS:** Based on the document context provided above, give a comprehensive and accurate answer to the question. If the context doesn't contain sufficient information, clearly explain what information is missing."""

class QwenRAGOptimizer:
    """Advanced optimization techniques for Qwen-2.5 RAG"""
    
    @staticmethod
    def detect_query_type(question: str) -> str:
        """Automatically detect the type of query to use appropriate prompting"""
        
        question_lower = question.lower()
        
        # Factual indicators
        if any(keyword in question_lower for keyword in FACTUAL_KEYWORDS):
            return "factual"
        
        # Analytical indicators
        if any(keyword in question_lower for keyword in ANALYTICAL_KEYWORDS):
            return "analytical"
        
        # Summarization indicators
        if any(keyword in question_lower for keyword in SUMMARY_KEYWORDS):
            return "summarization"
        
        return "general"
    
    @staticmethod
    def optimize_chunks_for_qwen(chunks: list, max_context_length: int = 4000) -> tuple[list, str]:
        """Optimize chunk selection and formatting specifically for Qwen-2.5"""
        
        if not chunks:
            return [], ""
        
        # Sort by similarity score
        # sorted_chunks = sorted(chunks, key=lambda x: x.get('similarity_score', 0), reverse=True)
        
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
    