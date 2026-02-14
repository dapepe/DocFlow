"""
OpenRouter LLaVA Models
LLaVA models via OpenRouter - open-source vision capabilities at scale
"""

import os

import structlog

from .openrouter_base import OpenRouterBaseModel
from . import ModelRegistry

logger = structlog.get_logger(__name__)


class OpenRouterLLaVAModel(OpenRouterBaseModel):
    """LLaVA model via OpenRouter - open-source vision-language model"""

    description = (
        "LLaVA via OpenRouter - High-quality open-source vision-language understanding"
    )

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the LLaVA model name"""
        return os.getenv("OPENROUTER_LLAVA_MODEL", "liuhaotian/llava-yi-34b")


# Register the OpenRouter LLaVA model
ModelRegistry.register("openrouter-llava", OpenRouterLLaVAModel)
