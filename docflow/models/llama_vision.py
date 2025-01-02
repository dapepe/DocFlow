"""
Llama Vision Model Implementation
Provides document analysis using Llama Vision model via Ollama
"""
from .ollama_base import OllamaBaseModel
from . import ModelRegistry
import os
import json
import base64
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class LlamaVisionModel(OllamaBaseModel):
    """Llama Vision model using Ollama for document analysis"""
    description = "Llama Vision model for advanced document analysis"

    # Document analysis schema
    ANALYSIS_SCHEMA = {
        "document_type": "Type of document (invoice, contract, report, etc.)",
        "dates": ["List of important dates found"],
        "amounts": ["List of monetary amounts"],
        "entities": {
            "organizations": ["Company names"],
            "people": ["Person names"]
        },
        "metadata": {
            "invoice_number": "Document reference number if present",
            "total_amount": "Total amount if present",
            "due_date": "Payment due date if present"
        }
    }

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the Llama Vision model name"""
        return os.getenv('OLLAMA_LLAMA_VISION_MODEL', 'llama3.2-vision:latest')

    def _get_prompt_template(self, text: str) -> str:
        """Get the prompt template for document analysis"""
        return f"""As a document analysis expert, analyze this document and extract key information in JSON format.

        Please structure your response according to this schema:
        {json.dumps(self.ANALYSIS_SCHEMA, indent=2)}

        Document content to analyze:
        {text}

        Provide ONLY the JSON response, no additional text.
        """

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information using Llama Vision model"""
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
            logger.error(f"Error in Llama Vision analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model
            }

    @classmethod
    def is_available(cls) -> bool:
        """Check if Ollama service is available and model is installed"""
        try:
            # Check if Ollama service is responding
            host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
            logger.debug(f"Checking Ollama availability at {host}")

            response = requests.get(f"{host}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                required_model = cls._get_model_name()
                available_models = [m.get('name', '') for m in models]
                logger.debug(f"Found Ollama models: {available_models}")

                is_model_available = required_model in available_models
                logger.debug(f"Required model {required_model} availability: {is_model_available}")
                return is_model_available

            logger.warning(f"Ollama service returned status code: {response.status_code}")
            return False

        except requests.exceptions.ConnectionError as e:
            logger.debug(f"Ollama service connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking Ollama availability: {e}")
            return False

# Register the Llama Vision model
ModelRegistry.register("llama-vision", LlamaVisionModel)