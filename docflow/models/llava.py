"""
LLaVA Model Implementation
Provides document analysis using LLaVA model via Ollama
"""
from .ollama_base import OllamaBaseModel
from . import ModelRegistry
import os
import json
import base64
from typing import Dict, Any, Optional
import logging
import requests

logger = logging.getLogger(__name__)

class LLaVAModel(OllamaBaseModel):
    """LLaVA model using Ollama for document analysis"""
    description = "LLaVA model for advanced document analysis"

    # Document analysis schema
    ANALYSIS_SCHEMA = {
        "document_type": "Type of document (invoice, contract, report, etc.)",
        "content_summary": "Brief summary of the document content",
        "key_points": ["List of important points or findings"],
        "entities": {
            "organizations": ["Company names"],
            "people": ["Person names"],
            "locations": ["Location names"]
        },
        "metadata": {
            "reference_number": "Document reference number if present",
            "date": "Document date if present",
            "category": "Document category or classification"
        },
        "visual_elements": ["Description of important visual elements if image is provided"]
    }

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the LLaVA model name"""
        return os.getenv('OLLAMA_LLAVA_MODEL', 'llava:latest')

    def _get_prompt_template(self, text: str) -> str:
        """Get the prompt template for document analysis"""
        return f"""As a document analysis expert, provide a comprehensive analysis of this document in JSON format.

        Structure your response according to this schema:
        {json.dumps(self.ANALYSIS_SCHEMA, indent=2)}

        Document content to analyze:
        {text}

        Provide ONLY the JSON response, no additional text.
        """

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information using LLaVA model"""
        try:
            # Prepare the request payload
            payload = {
                "model": self.model,
                "prompt": self._get_prompt_template(text),
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            }

            # Add image if available
            if image_path:
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    payload["images"] = [image_data]

            # Make request to Ollama API
            result = self._make_ollama_request(payload)
            analysis = result.get('response', '')

            # Try to extract structured information from the response
            try:
                structured_data = json.loads(analysis)
            except json.JSONDecodeError:
                structured_data = {"raw_text": analysis}

            return {
                "raw_analysis": structured_data,
                "model_name": self.model,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error in LLaVA analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model
            }

# Register the LLaVA model
ModelRegistry.register("llava", LLaVAModel)