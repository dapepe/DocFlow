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
from urllib3.util import Retry
import json
import re
from ..prompt_manager import prompt_manager
from ..response_validator import ResponseValidator
from ..performance_optimizer import cached_model_response, optimize_text_extraction

logger = logging.getLogger(__name__)

class OllamaBaseModel(BaseModel):
    """Base class for Ollama-based models"""
    description = "Base Ollama Model"
    requires_env_vars = []  # No required env vars since we have defaults

    # Default configuration
    DEFAULT_CONFIG = {
        'host': 'http://localhost:11434',
        'temperature': 0.2,
        'timeout': 60,  # Increased timeout
        'max_retries': 3,
        'retry_backoff_factor': 0.3,
        'retry_on_status': [408, 429, 500, 502, 503, 504],
    }

    def __init__(self):
        """Initialize the model with configuration from environment"""
        super().__init__()
        self.config = self._load_config()
        self.model = self._get_model_name()
        self.session = self._setup_requests_session()
        self.schema = self._load_schema()
        self.validator = ResponseValidator(self.schema)
        logger.info(f"Initialized Ollama model: {self.model} with schema and validator")

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
            logger.info(f"Checking Ollama availability at {host}")

            session = requests.Session()
            response = session.get(f"{host}/api/tags", timeout=30)

            if response.status_code == 200:
                models = response.json().get('models', [])
                required_model = cls._get_model_name()
                # Get base model name without version tag
                base_model = required_model.split(':')[0]

                available_models = [m.get('name', '') for m in models]
                logger.info(f"Available Ollama models: {available_models}")

                # Check if any model starts with our base model name
                is_model_available = any(
                    m.startswith(base_model)
                    for m in available_models
                )
                logger.info(f"Required model {required_model} availability: {is_model_available}")
                return is_model_available

            logger.warning(f"Ollama service returned status code: {response.status_code}")
            return False

        except requests.exceptions.ConnectionError as e:
            logger.info(f"Ollama service not available at {host}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking Ollama availability: {e}")
            return False

    def _load_schema(self) -> dict:
        """Load JSON schema from file"""
        schema_path = os.getenv('DOCFLOW_SCHEMA_PATH', 'config/schema.json')
        try:
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema from {schema_path}: {e}")
            raise

    def _generate_enhanced_prompt(self, text: str, document_type: Optional[str] = None, 
                                 file_extension: Optional[str] = None) -> str:
        """Generate an enhanced prompt using the configurable prompt system"""
        model_instructions = prompt_manager.get_model_specific_instructions(
            self.__class__.__name__.replace('Model', '').lower().replace('ollama', '').replace('base', '')
        )
        
        return prompt_manager.generate_prompt(
            document_text=text,
            schema=self.schema,
            document_type=document_type,
            file_extension=file_extension,
            model_specific_instructions=model_instructions
        )

    def _make_request(self, prompt: str) -> Dict[str, Any]:
        """Make a request to Ollama API with proper formatting"""
        url = f"{self.config['host']}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": self.schema,
            "options": {
                "temperature": self.config['temperature']
                # Removed stop sequence to get complete response
            }
        }

        try:
            response = self.session.post(url, json=payload, timeout=self.config['timeout'])
            response.raise_for_status()
            
            # Get the complete response text
            response_text = ""
            for line in response.text.strip().split('\n'):
                if line:
                    try:
                        json_response = json.loads(line)
                        if 'response' in json_response:
                            response_text += json_response['response']
                    except json.JSONDecodeError:
                        continue

            # Clean up and complete the response if necessary
            response_text = response_text.strip()
            
            # Complete any incomplete JSON structure
            open_braces = response_text.count('{')
            close_braces = response_text.count('}')
            if open_braces > close_braces:
                response_text += '}' * (open_braces - close_braces)
            
            # Ensure we have a complete JSON object
            if not response_text.startswith('{'):
                response_text = '{' + response_text
            if not response_text.endswith('}'):
                response_text += '}'

            # Try to parse the JSON
            try:
                # First try to parse as is
                return json.loads(response_text)
            except json.JSONDecodeError:
                try:
                    # Fix common formatting issues
                    fixed_text = response_text.replace("'", '"')  # Replace single quotes
                    fixed_text = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', fixed_text)  # Quote property names
                    fixed_text = re.sub(r',\s*}', '}', fixed_text)  # Remove trailing commas
                    fixed_text = re.sub(r'}\s*{', '},{', fixed_text)  # Fix adjacent objects
                    
                    # Complete any incomplete structures
                    if '"amounts": {' in fixed_text and '"amounts": {}' not in fixed_text:
                        fixed_text = fixed_text.replace('"amounts": {', '"amounts": {}')
                    if '"dates": {' in fixed_text and '"dates": {}' not in fixed_text:
                        fixed_text = fixed_text.replace('"dates": {', '"dates": {}')
                    if '"entities": {' in fixed_text and '"entities": {}' not in fixed_text:
                        fixed_text = fixed_text.replace('"entities": {', '"entities": {}')
                    
                    return json.loads(fixed_text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}\nResponse text: {response_text}")
                    return {"error": "Invalid JSON response"}
            
        except Exception as e:
            logger.error(f"Ollama API request failed: {e}")
            raise