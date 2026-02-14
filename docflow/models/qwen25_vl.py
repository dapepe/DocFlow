"""
Qwen2.5-VL Model Implementation

Provides document analysis using Qwen2.5-Vision-Language model via llama.cpp.
Optimized for multilingual document understanding and visual analysis.
"""

import os
from typing import Dict, Any, Optional
from .providers import LlamaCppProvider
from . import ModelRegistry
import structlog

logger = structlog.get_logger(__name__)


class Qwen25VLModel(LlamaCppProvider):
    """
    Qwen2.5-VL model using llama.cpp for document analysis.

    Excellent for:
    - Multilingual documents (100+ languages)
    - Visual document understanding
    - OCR and text extraction from images
    - Structured data extraction
    """

    description = (
        "Qwen2.5-VL (GGUF) - Multilingual vision-language model for document analysis"
    )
    requires_env_vars = ["LLAMA_CPP_QWEN25_VL_PATH"]

    @classmethod
    def _get_model_path(cls) -> str:
        """Get the Qwen2.5-VL GGUF model path."""
        return os.getenv(
            "LLAMA_CPP_QWEN25_VL_PATH",
            os.path.expanduser("~/models/qwen2.5-vl-7b-instruct-q4_k_m.gguf"),
        )

    def __init__(self):
        """Initialize Qwen2.5-VL with optimized settings."""
        super().__init__()
        # Qwen2.5-VL works best with larger context for documents
        if self.config["n_ctx"] < 8192:
            logger.warning(
                "qwen25vl_context_window_suboptimal",
                current_n_ctx=self.config["n_ctx"],
                recommended_n_ctx=8192,
            )

    def get_capabilities(self) -> Dict[str, bool]:
        """Get Qwen2.5-VL capabilities."""
        caps = super().get_capabilities()
        caps.update(
            {
                "multilingual": True,
                "vision": True,
                "ocr": True,
                "max_context": self.config["n_ctx"],
            }
        )
        return caps


# Register the model
ModelRegistry.register("qwen2.5-vl", Qwen25VLModel)
logger.info("model_registered", model_id="qwen2.5-vl", provider="llama.cpp")
