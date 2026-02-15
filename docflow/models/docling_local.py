"""
Docling Local Model Implementation

Integration with IBM Docling for advanced document layout analysis and OCR.
Runs locally using the docling python library.
"""

import os
import json
import structlog
from typing import Dict, Any, Optional
from pathlib import Path
from docflow.models.providers.base import LocalProvider
from docflow.prompt_manager import prompt_manager
from docflow.response_validator import ResponseValidator

logger = structlog.get_logger(__name__)


class DoclingLocalModel(LocalProvider):
    """
    IBM Docling integration for local document processing.

    Excellent for:
    - PDF table extraction
    - Layout analysis
    - Scientific papers and technical docs
    - Complex formatting preservation
    """

    description = "Docling (Local) - Advanced layout analysis and table extraction"
    requires_env_vars = []  # No specific env vars needed, uses local libs

    # Default configuration
    DEFAULT_CONFIG = {
        "ocr_enabled": True,
        "table_structure": True,
        "do_ocr": True,
    }

    def __init__(self):
        """Initialize Docling model."""
        super().__init__()
        self.pipeline = None  # Lazy initialization
        self.doc_converter = None

        # Set capabilities
        self.capabilities.local = True
        self.capabilities.ocr = True
        self.capabilities.vision = True
        self.capabilities.structured_output = True  # Can produce JSON/Markdown
        self.capabilities.document_specialized = True

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        return self.DEFAULT_CONFIG.copy()

    def _load_model(self):
        """Load Docling pipeline."""
        try:
            from docling.document_converter import DocumentConverter
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.datamodel.base_models import InputFormat

            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = self.config["do_ocr"]
            pipeline_options.do_table_structure = self.config["table_structure"]

            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: pipeline_options,
                    InputFormat.IMAGE: pipeline_options,
                }
            )
            logger.info("docling_model_loaded")
            return converter

        except ImportError:
            logger.error(
                "docling_library_missing", message="Install with: pip install docling"
            )
            raise RuntimeError("docling package is required")
        except Exception as e:
            logger.error("docling_load_failed", error=str(e))
            raise

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Docling is an extraction model, not a generative model.
        It doesn't 'generate' text from prompts in the LLM sense.
        This method is here to satisfy the interface but might be unused
        if extract_information is called directly.
        """
        return "Docling does not support text generation. Use extract_information()."

    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process document with Docling.

        Note: Docling works on FILES, not raw text strings.
        If 'image_path' is provided, we use that.
        If only 'text' is provided, we can't really run Docling on it unless it's a file path string.
        """
        self._ensure_model_loaded()

        # Determine input file
        input_path = image_path
        if not input_path and text and os.path.exists(text):
            input_path = text

        if not input_path:
            return {
                "success": False,
                "error": "Docling requires a valid file path (image or PDF)",
                "model_name": "docling-local",
                "provider": "docling",
            }

        try:
            logger.info("processing_with_docling", path=input_path)

            # Run conversion
            # self.model is the DocumentConverter instance
            result = self.model.convert(input_path)

            # Export to markdown/json
            markdown_content = result.document.export_to_markdown()
            json_content = result.document.export_to_dict()

            # Since Docling just extracts, we might want to wrap this in a structure
            # matching our schema if possible, OR just return the raw extraction.
            # Ideally, we should pass this Markdown to an LLM for final structuring,
            # but this class represents the "Model" itself.
            # For now, we return the structured content in raw_analysis.

            return {
                "raw_analysis": json_content,
                "extracted_text": markdown_content,
                "model_name": "docling-local",
                "success": True,
                "validation_passed": True,  # It's extraction, not generation validation
                "provider": "docling",
            }

        except Exception as e:
            logger.error("docling_processing_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "model_name": "docling-local",
                "provider": "docling",
            }

    async def extract_information_async(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Async wrapper for extraction."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.extract_information, text, image_path
        )

    @classmethod
    def is_available(cls) -> bool:
        """Check if docling library is installed."""
        try:
            import docling

            return True
        except ImportError:
            return False


# Register
from docflow.models import ModelRegistry

ModelRegistry.register("docling-local", DoclingLocalModel)
