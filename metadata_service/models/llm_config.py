import os
import logging

logger = logging.getLogger(__name__)

class ModelConfig:
    """Configuration class for the model"""
    
    def __init__(self):
        self.model_name = os.environ["OPENAI_MODEL"]
        
        # Qwen-2.5 generation parameters optimized for RAG
        self.generation_params = {
            "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.1")),
            "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", "2000")),
            "top_p": float(os.getenv("MODEL_TOP_P", "0.8")),
            "frequency_penalty": float(os.getenv("MODEL_FREQ_PENALTY", "0.1")),
            "presence_penalty": float(os.getenv("MODEL_PRESENCE_PENALTY", "0.1")),
        }

        self.enable_response_post_processing = os.getenv("ENABLE_RESPONSE_POST_PROCESSING", "true").lower() == "true"

class PromptTemplates:
    """Specialized prompt templates"""

    @staticmethod
    def get_system_prompt(purpose: str) -> str:
        """Generate system prompt for model based on query context and purpose of service"""
        
        system_prompts = {
            "summary": """You are an expert at document summarization and synthesis.

Your summarization strategy:
- Identify the main themes and key points from the context
- Organize information hierarchically (main points, supporting details)
- Preserve important nuances and qualifications
- Maintain the original document's tone and perspective
- Create coherent summaries that capture essential information
- Use bullet points or structured format when appropriate for clarity
- Ensure summaries are concise yet comprehensive
""",
            "default": """If the question cannot be answered, return only the stop token."""
}

        return system_prompts.get(purpose)

    @staticmethod
    def get_user_prompt(question: str, purpose: str) -> str:
        """Generate user prompt"""

        user_prompts = {
            "summary": f"""
**SUMMARIZATION REQUEST:** {question}

**INSTRUCTIONS:** Create a well-structured summary addressing the request. Organize the information logically and maintain the document's key insights and perspective.""",
            "title": f"""
**QUERY REQUEST:** {question}

**INSTRUCTIONS:** Return the title in the following format:
    Title: Title
""",
            "authors": f"""
**QUERY REQUEST:** {question}

**INSTRUCTIONS:** Return the list of authors in the following format:
    Authors: Author1, Author2, Author3, etc
""",
            "keywords": f"""
**QUERY REQUEST:** {question}

**INSTRUCTIONS:** Return the list of keywords in the following format:
    Keywords: keyword1, keyword2, keyword3, etc
"""
}

        return user_prompts.get(purpose)

class ModelResponseOptimizer:
    """Advanced optimization techniques for the model"""

    @staticmethod
    def post_process_llm_response(response: str) -> str:
        """Post-process LLM response for better formatting"""
        
        # Remove only consecutive duplicate lines to avoid breaking formatted content.
        lines = response.split('\n')
        if not lines:
            return ""

        filtered_lines = [lines[0]]
        for i in range(1, len(lines)):
            current_line_stripped = lines[i].strip()
            prev_line_stripped = lines[i-1].strip()
            if not current_line_stripped or current_line_stripped != prev_line_stripped:
                filtered_lines.append(lines[i])
        
        cleaned_response = '\n'.join(filtered_lines)
        
        # Ensure response ends properly
        if cleaned_response and not cleaned_response.rstrip().endswith(('.', '!', '?', ':')):
            cleaned_response = cleaned_response.rstrip() + '.'
        
        return cleaned_response.strip()