"""
OpenRouter GPT-4 Vision Model
OpenAI's GPT-4 Vision via OpenRouter - often cheaper than direct OpenAI API
"""
from .openrouter_base import OpenRouterBaseModel
from . import ModelRegistry
import os

class OpenRouterGPT4VisionModel(OpenRouterBaseModel):
    """GPT-4 Vision model via OpenRouter for cost-effective premium analysis"""
    description = "GPT-4 Vision via OpenRouter - Premium vision analysis with competitive pricing"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the GPT-4 Vision model name"""
        return os.getenv('OPENROUTER_GPT4_VISION_MODEL', 'openai/gpt-4-vision-preview')

# Register the OpenRouter GPT-4 Vision model
ModelRegistry.register("openrouter-gpt4-vision", OpenRouterGPT4VisionModel)