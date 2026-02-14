"""
OpenRouter Gemini Vision Models
Google's Gemini models via OpenRouter - excellent value for document processing
"""

import os

import structlog

from .openrouter_base import OpenRouterBaseModel
from . import ModelRegistry

logger = structlog.get_logger(__name__)


class OpenRouterGeminiFlashModel(OpenRouterBaseModel):
    """Gemini 1.5 Flash model via OpenRouter - fast and cost-effective"""

    description = "Gemini 1.5 Flash via OpenRouter - Fast, accurate, and cost-effective document analysis"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Gemini Flash model name"""
        return os.getenv("OPENROUTER_GEMINI_FLASH_MODEL", "google/gemini-flash-1.5")


class OpenRouterGeminiProModel(OpenRouterBaseModel):
    """Gemini 1.5 Pro model via OpenRouter - premium performance"""

    description = "Gemini 1.5 Pro via OpenRouter - Premium document analysis with advanced reasoning"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Gemini Pro model name"""
        return os.getenv("OPENROUTER_GEMINI_PRO_MODEL", "google/gemini-pro-1.5")


# Register the OpenRouter Gemini models
ModelRegistry.register("openrouter-gemini-flash", OpenRouterGeminiFlashModel)
ModelRegistry.register("openrouter-gemini-pro", OpenRouterGeminiProModel)
