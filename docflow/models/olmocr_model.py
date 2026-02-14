"""
olmOCR Model Implementation

Specialized OCR model for document text extraction.
Fine-tuned specifically for extracting text from document images.
"""

import os
from typing import Dict, Any
from .providers import LlamaCppProvider
from . import ModelRegistry
import structlog

logger = structlog.get_logger(__name__)


class OlmOCRModel(LlamaCppProvider):
    """
    olmOCR specialized model using llama.cpp for document OCR.

    Excellent for:
    - High-accuracy text extraction from images
    - Document OCR with layout preservation
    - Handwritten and printed text recognition
    - Multi-page document processing

    Note: This model is specifically trained for OCR tasks and may not
    perform general document analysis as well as general vision models.
    """

    description = "olmOCR (GGUF) - Specialized OCR model for document text extraction"
    requires_env_vars = ["LLAMA_CPP_OLMOCR_PATH"]

    @classmethod
    def _get_model_path(cls) -> str:
        """Get the olmOCR GGUF model path."""
        return os.getenv(
            "LLAMA_CPP_OLMOCR_PATH",
            os.path.expanduser("~/models/olmOCR-7b-q4_k_m.gguf"),
        )

    def __init__(self):
        """Initialize olmOCR with OCR-optimized settings."""
        super().__init__()
        # olmOCR works best with specific settings
        if self.config["n_ctx"] < 4096:
            logger.info("olmocr_context_window_adjusted", n_ctx=4096)
            self.config["n_ctx"] = 4096

    def get_capabilities(self) -> Dict[str, bool]:
        """Get olmOCR capabilities."""
        caps = super().get_capabilities()
        caps.update(
            {
                "vision": True,
                "ocr": True,
                "specialized_ocr": True,
                "general_analysis": False,  # Focused on OCR, not general QA
            }
        )
        return caps


# Register the model
ModelRegistry.register("olmocr-7b", OlmOCRModel)
logger.info("model_registered", model_id="olmocr-7b", provider="llama.cpp")
