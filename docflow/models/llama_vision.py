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
    requires_env_vars = ['OLLAMA_HOST', 'OLLAMA_MODEL']

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

    @classmethod
    def is_available(cls) -> bool:
        """Check if Ollama service is available and model is installed"""
        try:
            host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
            response = requests.get(f"{host}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                required_model = os.getenv('OLLAMA_MODEL', 'llama-3.2-vision')
                logger.debug(f"Checking Llama Vision availability: Found models: {[m['name'] for m in models]}")
                return any(m['name'] == required_model for m in models)
            logger.debug("Ollama service not responding correctly")
            return False
        except Exception as e:
            logger.debug(f"Ollama service not available: {e}")
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

            # Make request to Ollama API
            response = requests.post(f"{self.host}/api/generate", json=payload)
            response.raise_for_status()

            # Parse response
            result = response.json()
            analysis = result.get('response', '')

            # Try to extract structured information from the response
            try:
                # Attempt to parse if response is JSON
                structured_data = json.loads(analysis)
            except json.JSONDecodeError:
                # If not JSON, provide as raw text
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

# Register Llama Vision models
ModelRegistry.register("llama-vision", LlamaVisionModel)
ModelRegistry.register("llava", LlamaVisionModel)  # Register LLaVA as an alias