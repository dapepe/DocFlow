"""
Llama Vision Model Implementation
Provides document analysis using Llama Vision model via Ollama
"""

from .ollama_base import OllamaBaseModel
from . import ModelRegistry
import os
import base64
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class LlamaVisionModel(OllamaBaseModel):
    """Llama Vision model using Ollama for document analysis"""

    description = "Llama Vision model for advanced document analysis"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Llama Vision model name"""
        return os.getenv("OLLAMA_LLAMA_VISION_MODEL", "llama3.2-vision:latest")

    def _get_enhanced_prompt(
        self, text: str, document_type: str = None, file_extension: str = None
    ) -> str:
        """Get enhanced prompt using the configurable prompt system"""
        return self._generate_enhanced_prompt(text, document_type, file_extension)

    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information from text and/or image using Llama Vision"""
        try:
            prompt = self._get_enhanced_prompt(text)

            # Add image if available
            if image_path:
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode("utf-8")
                    self.images = [image_data]

            # Make the API request using the base class method
            response = self._make_request(prompt)

            if isinstance(response, dict) and "error" not in response:
                return {
                    "raw_analysis": response,
                    "model_name": self.model,
                    "success": True,
                }
            else:
                logger.error("invalid_response_from_llama_vision", response=response)
                return {
                    "success": False,
                    "error": "Failed to get valid response from Llama Vision",
                    "model_name": self.model,
                }

        except Exception as e:
            logger.error("llama_vision_analysis_error", error=str(e), exc_info=True)
            return {"success": False, "error": str(e), "model_name": self.model}


# Register the Llama Vision model
ModelRegistry.register("llama-vision", LlamaVisionModel)
