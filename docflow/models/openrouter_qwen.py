"""
OpenRouter Qwen Vision Models
Alibaba's Qwen models via OpenRouter - excellent multilingual capabilities
"""

import os

import structlog

from .openrouter_base import OpenRouterBaseModel
from . import ModelRegistry

logger = structlog.get_logger(__name__)


class OpenRouterQwenVLModel(OpenRouterBaseModel):
    """Qwen2-VL model via OpenRouter - excellent for multilingual documents"""

    description = "Qwen2-VL via OpenRouter - Advanced multilingual document analysis with vision capabilities"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Qwen VL model name"""
        return os.getenv("OPENROUTER_QWEN_VL_MODEL", "qwen/qwen-2-vl-72b-instruct")


# Register the OpenRouter Qwen model
ModelRegistry.register("openrouter-qwen-vl", OpenRouterQwenVLModel)
