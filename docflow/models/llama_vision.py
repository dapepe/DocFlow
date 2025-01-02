"""
Llama Vision Model Implementation
Provides document analysis using Llama/LLaVA models via Ollama
"""
import os
import json
import requests
from typing import Dict, Any, Optional
from . import BaseModel, ModelRegistry
import logging

logger = logging.getLogger(__name__)

class LlamaVisionModel(BaseModel):
    """Llama Vision model using Ollama for document analysis"""
    description = "Llama Vision model (requires Ollama installation)"
    requires_env_vars = ['OLLAMA_HOST']  # Only require host, model has default

    def __init__(self):
        """Initialize the model with configuration from environment"""
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama-3.2-vision')
        self.prompt_template = os.getenv('OLLAMA_PROMPT_TEMPLATE', 
            """Analyze this document and extract key information:
            1. Document type/category
            2. Important dates
            3. Monetary amounts
            4. Key entities (people, companies)
            5. Important details specific to the document type

            Provide the analysis in a structured format.
            """)
        logger.debug(f"Initialized LlamaVision with host={self.host}, model={self.model}")

    @classmethod
    def is_available(cls) -> bool:
        """Check if Ollama service is available and model is installed"""
        try:
            # First check if required environment variables are set
            if not super().is_available():
                logger.debug("LlamaVision environment variables not configured")
                return False

            # Then check if Ollama service is responding
            host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
            logger.debug(f"Checking Ollama availability at {host}")

            response = requests.get(f"{host}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                required_model = os.getenv('OLLAMA_MODEL', 'llama-3.2-vision')
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

    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information using Llama Vision model"""
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
            logger.error(f"Error in Llama Vision analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model
            }

# Register both model variants
ModelRegistry.register("llama-vision", LlamaVisionModel)
ModelRegistry.register("llava", LlamaVisionModel)  # Register LLaVA as an alias