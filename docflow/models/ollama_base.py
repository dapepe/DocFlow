"""
Base Ollama Model Implementation
Provides shared functionality for Ollama-based models
"""
import os
import json
import requests
from typing import Dict, Any, Optional
from . import BaseModel
import logging

logger = logging.getLogger(__name__)

class OllamaBaseModel(BaseModel):
    """Base class for Ollama-based models"""
    description = "Base Ollama Model"
    requires_env_vars = []  # No required env vars since we have defaults

    def __init__(self):
        """Initialize the model with configuration from environment"""
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = self._get_model_name()
        self.prompt_template = os.getenv('OLLAMA_PROMPT_TEMPLATE', 
            """Analyze this document and extract key information:
            1. Document type/category
            2. Important dates
            3. Monetary amounts
            4. Key entities (people, companies)
            5. Important details specific to the document type

            Provide the analysis in a structured format.
            """)
        logger.debug(f"Initialized Ollama model with host={self.host}, model={self.model}")

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the model name with proper format. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _get_model_name")

    @classmethod
    def is_available(cls) -> bool:
        """Check if Ollama service is available and the required model is installed"""
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

                # Check if the model exists (including version tag)
                is_model_available = any(
                    m.startswith(required_model.split(':')[0])
                    for m in available_models
                )
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

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information using Ollama model"""
        try:
            # Prepare the request payload
            payload = {
                "model": self.model,
                "prompt": self.prompt_template,
                "stream": False
            }

            # Add image if available
            if image_path:
                import base64
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    payload["images"] = [image_data]

            # Add text context
            if text:
                payload["context"] = text

            logger.debug(f"Making request to Ollama API at {self.host}")
            response = requests.post(f"{self.host}/api/generate", json=payload)
            response.raise_for_status()

            # Parse response
            result = response.json()
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
            logger.error(f"Error in Ollama analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model
            }
