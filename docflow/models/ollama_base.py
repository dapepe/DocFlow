"""
Base Ollama Model Implementation
Provides shared functionality for Ollama-based models
"""
import os
import requests
from typing import Dict, Any, Optional
from . import BaseModel
import logging
from requests.adapters import HTTPAdapter
from urllib3.util import Retry  # Updated import to fix the LSP issue

logger = logging.getLogger(__name__)

class OllamaBaseModel(BaseModel):
    """Base class for Ollama-based models"""
    description = "Base Ollama Model"
    requires_env_vars = []  # No required env vars since we have defaults

    # Default configuration
    DEFAULT_CONFIG = {
        'host': 'http://localhost:11434',
        'temperature': 0.2,
        'timeout': 30,
        'max_retries': 3,
        'retry_backoff_factor': 0.3,
        'retry_on_status': [408, 429, 500, 502, 503, 504],
    }

    def __init__(self):
        """Initialize the model with configuration from environment"""
        self.config = self._load_config()
        self.model = self._get_model_name()
        self.session = self._setup_requests_session()
        logger.debug(f"Initialized Ollama model with config={self.config}, model={self.model}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables with defaults"""
        config = self.DEFAULT_CONFIG.copy()

        # Override defaults with environment variables if present
        env_mapping = {
            'OLLAMA_HOST': ('host', str),
            'OLLAMA_TEMPERATURE': ('temperature', float),
            'OLLAMA_TIMEOUT': ('timeout', int),
            'OLLAMA_MAX_RETRIES': ('max_retries', int),
            'OLLAMA_RETRY_BACKOFF': ('retry_backoff_factor', float),
        }

        for env_var, (config_key, type_func) in env_mapping.items():
            if value := os.getenv(env_var):
                try:
                    config[config_key] = type_func(value)
                except ValueError as e:
                    logger.warning(f"Invalid value for {env_var}: {e}")

        return config

    def _setup_requests_session(self) -> requests.Session:
        """Set up a requests session with retry logic"""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.config['max_retries'],
            backoff_factor=self.config['retry_backoff_factor'],
            status_forcelist=self.config['retry_on_status']
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the model name with proper format. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _get_model_name")

    @classmethod
    def is_available(cls) -> bool:
        """Check if Ollama service is available and the required model is installed"""
        try:
            # Check if Ollama service is responding
            host = os.getenv('OLLAMA_HOST', cls.DEFAULT_CONFIG['host'])
            logger.debug(f"Checking Ollama availability at {host}")

            session = requests.Session()
            response = session.get(f"{host}/api/tags", timeout=5)  # Added timeout

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
            # Verify service availability before making request
            if not self.is_available():
                raise Exception(f"Ollama service or model {self.model} is not available")

            # Add default options if not present
            if 'options' not in payload:
                payload['options'] = {}
            if 'temperature' not in payload['options']:
                payload['options']['temperature'] = self.config['temperature']

            logger.debug(f"Making request to Ollama API at {self.config['host']}")
            response = self.session.post(
                f"{self.config['host']}/api/generate",
                json=payload,
                timeout=self.config['timeout']
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise Exception(f"Failed to communicate with Ollama service: {str(e)}")
        except Exception as e:
            logger.error(f"Error in Ollama request: {e}")
            raise