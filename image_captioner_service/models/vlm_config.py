import os


class VLMConfig:
    """Configuration class for the optimization of the model's caption generation"""
    
    def __init__(self):
        self.model_name = os.getenv("OPENAI_VLM")
        
        # LLM's Generation parameters
        self.generation_params = {
            "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.1")),
            "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", "500")),
            "top_p": float(os.getenv("MODEL_TOP_P", "0.9")),
            "frequency_penalty": float(os.getenv("MODEL_FREQ_PENALTY", "0.1")),
            "presence_penalty": float(os.getenv("MODEL_PRESENCE_PENALTY", "0.1")),
        }
        
        # Context management
        self.enable_response_post_processing = os.getenv("ENABLE_RESPONSE_POST_PROCESSING", "true").lower() == "true"


class PromptTemplates:
    """Specialized prompt templates for the VLM"""

    @staticmethod
    def get_system_prompt() -> str:
        """System prompt instructing the VLM to act as an expert image analyst.
        It emphasizes accuracy and objectivity, tailored for document images."""
        
        system_prompt = """
            You are a highly specialized AI assistant for visual analysis and image captioning. Your sole purpose is to analyze an image and generate a concise, factual, and descriptive caption.

**Core Directives:**
1.  **Describe, Do Not Invent:** Your description must be based *strictly* on the visual information present in the image. Do not infer, assume, or hallucinate details that are not explicitly visible.
2.  **Identify the Image Type:** First, identify the type of image you are seeing (e.g., a photograph, a bar chart, a line graph, a table, a diagram, a screenshot). This will frame your description.
3.  **Be Objective and Neutral:** Use a neutral, descriptive tone. Avoid subjective language, opinions, or emotional interpretations.
4.  **Conciseness is Key:** Provide a single, well-formed paragraph for the caption. It should be comprehensive yet brief.

**Content-Specific Instructions:**
-   **For Tables:** Do not transcribe the entire table. Instead, describe its structure and content (e.g., "A table with 5 columns and 10 rows showing sales data, with columns for 'Product', 'Region', and 'Revenue'.").
-   **For Charts & Graphs:** Identify the chart type (e.g., 'bar chart', 'pie chart'). Describe what the axes represent and the main trend or finding it illustrates (e.g., "A bar chart illustrating a steady increase in user engagement from 2020 to 2024.").
-   **For Photographs or Scans:** Describe the main subject(s), the setting, and any significant actions or objects.
-   **For Diagrams & Flowcharts:** Briefly explain the process or system the diagram illustrates.
        """
        
        return system_prompt

class CaptionOptimizer:
    """Applies advanced post-processing to clean and format the generated caption."""

    @staticmethod
    def post_process_llm_response(response: str) -> str:
        """Cleans and standardizes the raw LLM output to ensure it's a high-quality caption."""
        
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
