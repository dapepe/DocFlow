"""
Gemma3 Model Implementation
Provides document analysis using Gemma3 model via Ollama
"""

from .ollama_base import OllamaBaseModel
from . import ModelRegistry
import os
import base64
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class GemmaModel(OllamaBaseModel):
    """Gemma3 model using Ollama for document analysis"""

    description = "Gemma3 model for advanced document analysis"

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Gemma model name"""
        return os.getenv("OLLAMA_GEMMA_MODEL", "gemma3:12b")

    def _get_enhanced_prompt(
        self, text: str, document_type: str = None, file_extension: str = None
    ) -> str:
        """Get enhanced prompt using the configurable prompt system"""
        return self._generate_enhanced_prompt(text, document_type, file_extension)

    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information from text and/or image using Gemma"""
        try:
            prompt = self._get_enhanced_prompt(text)

            # Add image if available (though Gemma3:12b is primarily text-based)
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
                logger.error("invalid_response_from_gemma", response=response)
                return {
                    "success": False,
                    "error": "Failed to get valid response from Gemma",
                    "model_name": self.model,
                }

        except Exception as e:
            logger.error("gemma_analysis_error", error=str(e), exc_info=True)
            return {"success": False, "error": str(e), "model_name": self.model}


# Register the Gemma model
ModelRegistry.register("gemma", GemmaModel)
