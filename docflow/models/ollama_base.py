"""
Base Ollama Model Implementation
Provides shared functionality for Ollama-based models
"""
import os
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

    def _make_ollama_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to Ollama API with proper error handling"""
        try:
            logger.debug(f"Making request to Ollama API at {self.host}")
            response = requests.post(f"{self.host}/api/generate", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in Ollama request: {e}")
            raise