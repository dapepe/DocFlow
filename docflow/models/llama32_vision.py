"""
Llama 3.2 Vision Model Implementation

Provides document analysis using Llama 3.2 Vision model via llama.cpp.
Balanced performance for both text and visual document understanding.
"""

import os
from typing import Dict, Any
from .providers import LlamaCppProvider
from . import ModelRegistry
import structlog

logger = structlog.get_logger(__name__)


class Llama32VisionModel(LlamaCppProvider):
    """
    Llama 3.2 Vision model using llama.cpp for document analysis.

    Excellent for:
    - General document understanding
    - Visual question answering
    - Text extraction from images
    - Balanced performance/quality tradeoff
    """

    description = (
        "Llama 3.2 Vision (GGUF) - Balanced vision-language model for documents"
    )
    requires_env_vars = ["LLAMA_CPP_LLAMA32_VISION_PATH"]

    @classmethod
    def _get_model_path(cls) -> str:
        """Get the Llama 3.2 Vision GGUF model path."""
        return os.getenv(
            "LLAMA_CPP_LLAMA32_VISION_PATH",
            os.path.expanduser("~/models/Llama-3.2-11B-Vision-Instruct-Q4_K_M.gguf"),
        )

    def __init__(self):
        """Initialize Llama 3.2 Vision with optimized settings."""
        super().__init__()
        # Llama 3.2 Vision uses different chat format
        self.config["chat_format"] = "llama-3"

    def get_capabilities(self) -> Dict[str, bool]:
        """Get Llama 3.2 Vision capabilities."""
        caps = super().get_capabilities()
        caps.update(
            {
                "multilingual": True,
                "vision": True,
                "ocr": True,
                "balanced": True,
            }
        )
        return caps


# Register the model
ModelRegistry.register("llama3.2-vision", Llama32VisionModel)
logger.info("Registered llama3.2-vision model (llama.cpp GGUF)")
