"""
LLaVA Model Implementation
Provides document analysis using LLaVA model via Ollama
"""
from .ollama_base import OllamaBaseModel
from . import ModelRegistry
import os

class LLaVAModel(OllamaBaseModel):
    """LLaVA model using Ollama for document analysis"""
    description = "LLaVA model for advanced document analysis"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the LLaVA model name"""
        return os.getenv('OLLAMA_LLAVA_MODEL', 'llava:latest')

# Register the LLaVA model
ModelRegistry.register("llava", LLaVAModel)
