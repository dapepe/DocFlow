"""
Qwen2.5 Vision Model Implementation
Provides document analysis using Qwen2.5 Vision model via Ollama
"""

from .ollama_base import OllamaBaseModel
from . import ModelRegistry
import os
import base64
from typing import Dict, Any, Optional
import structlog
from ..performance_optimizer import cached_model_response, optimize_text_extraction

logger = structlog.get_logger(__name__)


class QwenVisionModel(OllamaBaseModel):
    """Qwen2.5 Vision model using Ollama for document analysis"""

    description = "Qwen2.5 Vision model for advanced document analysis"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Qwen Vision model name"""
        return os.getenv("OLLAMA_QWEN_VISION_MODEL", "qwen2.5-vl:7b")

    def _get_enhanced_prompt(
        self, text: str, document_type: str = None, file_extension: str = None
    ) -> str:
        """Get enhanced prompt using the configurable prompt system"""
        return self._generate_enhanced_prompt(text, document_type, file_extension)

    @cached_model_response
    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information from text and/or image using Qwen Vision"""
        try:
            # Optimize text for processing
            optimized_text = optimize_text_extraction(text)
            prompt = self._get_enhanced_prompt(optimized_text)

            # Add image if available
            if image_path:
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode("utf-8")
                    self.images = [image_data]

            # Make the API request using the base class method
            response = self._make_request(prompt)

            if isinstance(response, dict) and "error" not in response:
                # Validate and enhance response
                is_valid, errors, corrected_response = self.validator.validate_response(
                    response
                )

                result = {
                    "raw_analysis": corrected_response,
                    "model_name": self.model,
                    "success": True,
                    "validation_passed": is_valid,
                    "validation_errors": errors if errors else None,
                    "text_optimized": len(text) != len(optimized_text),
                }

                if not is_valid:
                    logger.warning(
                        "qwen_vision_validation_failed", validation_errors=errors
                    )

                return result
            else:
                logger.error("invalid_response_from_qwen_vision", response=response)
                return {
                    "success": False,
                    "error": "Failed to get valid response from Qwen Vision",
                    "model_name": self.model,
                }

        except Exception as e:
            logger.error("qwen_vision_analysis_error", error=str(e), exc_info=True)
            return {"success": False, "error": str(e), "model_name": self.model}


# Register the Qwen Vision model
ModelRegistry.register("qwen-vision", QwenVisionModel)
