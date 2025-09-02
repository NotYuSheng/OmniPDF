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

class PromptTemplates:
    """Specialized prompt templates"""

    @staticmethod
    def get_system_prompt() -> str:
        """Generate system prompt for model based on query context and purpose of service"""
        
        system_prompt = """You are an expert at document summarization and synthesis.

Your summarization strategy:
- Identify the main themes and key points from the context
- Organize information hierarchically (main points, supporting details)
- Preserve important nuances and qualifications
- Maintain the original document's tone and perspective
- Create coherent summaries that capture essential information
- Use bullet points or structured format when appropriate for clarity
- Ensure summaries are concise yet comprehensive"""
        
        return system_prompt
    
    @staticmethod
    def get_summary_user_prompt(question: str, context: str) -> str:
        """Generate user prompt with context and question"""
        
        summary_user_prompt = """
**DOCUMENT CONTEXT:** {context}

**SUMMARIZATION REQUEST:** {question}

**INSTRUCTIONS:** Create a well-structured summary addressing the request. Organize the information logically and maintain the document's key insights and perspective."""

        return summary_user_prompt
