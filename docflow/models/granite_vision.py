"""
Granite3.2 Vision Model Implementation
Provides document analysis using Granite3.2 Vision model via Ollama
"""

from .ollama_base import OllamaBaseModel
from . import ModelRegistry
import os
import base64
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class GraniteVisionModel(OllamaBaseModel):
    """Granite3.2 Vision model using Ollama for document analysis"""

    description = "Granite3.2 Vision model for advanced document analysis"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Granite Vision model name"""
        return os.getenv("OLLAMA_GRANITE_VISION_MODEL", "granite3.2-vision:latest")

    def _get_enhanced_prompt(
        self, text: str, document_type: str = None, file_extension: str = None
    ) -> str:
        """Get enhanced prompt using the configurable prompt system"""
        return self._generate_enhanced_prompt(text, document_type, file_extension)

    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information from text and/or image using Granite Vision"""
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
                logger.error("invalid_response_from_granite_vision", response=response)
                return {
                    "success": False,
                    "error": "Failed to get valid response from Granite Vision",
                    "model_name": self.model,
                }

        except Exception as e:
            logger.error("granite_vision_analysis_error", error=str(e), exc_info=True)
            return {"success": False, "error": str(e), "model_name": self.model}


# Register the Granite Vision model
ModelRegistry.register("granite-vision", GraniteVisionModel)
