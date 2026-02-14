"""
OpenRouter Claude 3.5 Sonnet Vision Model
Anthropic's Claude 3.5 Sonnet via OpenRouter - excellent for document analysis
"""

import os

import structlog

from .openrouter_base import OpenRouterBaseModel
from . import ModelRegistry

logger = structlog.get_logger(__name__)


class OpenRouterClaudeModel(OpenRouterBaseModel):
    """Claude 3.5 Sonnet model via OpenRouter for premium document analysis"""

    description = "Claude 3.5 Sonnet via OpenRouter - Premium document understanding with exceptional reasoning"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Claude model name"""
        return os.getenv("OPENROUTER_CLAUDE_MODEL", "anthropic/claude-3.5-sonnet:beta")


# Register the OpenRouter Claude model
ModelRegistry.register("openrouter-claude", OpenRouterClaudeModel)
