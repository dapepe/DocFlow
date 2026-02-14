"""
OpenRouter Pixtral Model
Mistral's Pixtral vision model via OpenRouter - excellent document OCR
"""

import os

import structlog

from .openrouter_base import OpenRouterBaseModel
from . import ModelRegistry

logger = structlog.get_logger(__name__)


class OpenRouterPixtralModel(OpenRouterBaseModel):
    """Pixtral model via OpenRouter - specialized in document OCR and analysis"""

    description = (
        "Pixtral via OpenRouter - Advanced OCR and document understanding capabilities"
    )

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Pixtral model name"""
        return os.getenv("OPENROUTER_PIXTRAL_MODEL", "mistralai/pixtral-12b")


# Register the OpenRouter Pixtral model
ModelRegistry.register("openrouter-pixtral", OpenRouterPixtralModel)
