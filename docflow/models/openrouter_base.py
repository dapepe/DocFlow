"""
OpenRouter Base Model Implementation
Provides shared functionality for OpenRouter-based vision models
"""
import os
import requests
import json
import base64
import logging
import time
from typing import Dict, Any, Optional, List
from ..models import BaseModel
from . import ModelRegistry
from ..prompt_manager import prompt_manager
from ..response_validator import ResponseValidator
from ..performance_optimizer import cached_model_response, optimize_text_extraction

logger = logging.getLogger(__name__)

class OpenRouterBaseModel(BaseModel):
    """Base class for OpenRouter-based vision models"""
    description = "Base OpenRouter Vision Model"
    requires_env_vars = ['OPENROUTER_API_KEY']

    # Default configuration
    DEFAULT_CONFIG = {
        'api_base': 'https://openrouter.ai/api/v1',
        'temperature': 0.2,
        'max_tokens': 1000,
        'timeout': 120,
        'max_retries': 3,
    }

    def __init__(self):
        """Initialize the model with configuration from environment"""
        super().__init__()
        self.config = self._load_config()
        self.model = self._get_model_name()
        self.schema = self._load_schema()
        self.validator = ResponseValidator(self.schema)
        self.headers = self._setup_headers()
        logger.info(f"Initialized OpenRouter model: {self.model}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables with defaults"""
        config = self.DEFAULT_CONFIG.copy()
        
        env_mapping = {
            'OPENROUTER_API_BASE': ('api_base', str),
            'OPENROUTER_TEMPERATURE': ('temperature', float),
            'OPENROUTER_MAX_TOKENS': ('max_tokens', int),
            'OPENROUTER_TIMEOUT': ('timeout', int),
            'OPENROUTER_MAX_RETRIES': ('max_retries', int),
        }
        
        for env_var, (config_key, type_func) in env_mapping.items():
            if value := os.getenv(env_var):
                try:
                    config[config_key] = type_func(value)
                except ValueError as e:
                    logger.warning(f"Invalid value for {env_var}: {e}")
        
        return config

    def _setup_headers(self) -> Dict[str, str]:
        """Setup API request headers"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        app_name = os.getenv('OPENROUTER_APP_NAME', 'DocFlow')
        site_url = os.getenv('OPENROUTER_SITE_URL', 'https://github.com/docflow/docflow')
        
        return {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': site_url,
            'X-Title': app_name
        }

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the model name. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _get_model_name")

    @classmethod
    def is_available(cls) -> bool:
        """Check if OpenRouter API is available"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.debug(f"OpenRouter API key not found for {cls.__name__}")
            return False
        
        try:
            # Test API connectivity
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'https://openrouter.ai/api/v1/models',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                models = response.json().get('data', [])
                required_model = cls._get_model_name()
                
                # Check if our model is available
                available_models = [model.get('id', '') for model in models]
                is_available = required_model in available_models
                
                logger.debug(f"OpenRouter model {required_model} availability: {is_available}")
                return is_available
            else:
                logger.warning(f"OpenRouter API returned status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.debug(f"OpenRouter availability check failed: {e}")
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
            self._get_model_key()
        )
        
        return prompt_manager.generate_prompt(
            document_text=text,
            schema=self.schema,
            document_type=document_type,
            file_extension=file_extension,
            model_specific_instructions=model_instructions
        )

    def _get_model_key(self) -> str:
        """Get the model key for prompt instructions"""
        return self.__class__.__name__.lower().replace('model', '').replace('openrouter', '')

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _get_image_mime_type(self, image_path: str) -> str:
        """Get MIME type from image file extension"""
        extension = os.path.splitext(image_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_types.get(extension, 'image/jpeg')

    @cached_model_response
    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information from text and/or image using OpenRouter"""
        try:
            # Optimize text for processing
            optimized_text = optimize_text_extraction(text)
            prompt = self._generate_enhanced_prompt(optimized_text)
            
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert document analysis AI with advanced OCR and information extraction capabilities."
                }
            ]
            
            # Prepare content parts
            content_parts = [{"type": "text", "text": prompt}]
            
            # Add image if available
            if image_path:
                base64_image = self._encode_image(image_path)
                mime_type = self._get_image_mime_type(image_path)
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}",
                        "detail": "high"
                    }
                })
            
            messages.append({"role": "user", "content": content_parts})

            # Prepare API request
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.config['max_tokens'],
                "temperature": self.config['temperature'],
                "response_format": {"type": "json_object"}
            }

            # Make API request with retries
            for attempt in range(self.config['max_retries']):
                try:
                    response = requests.post(
                        f"{self.config['api_base']}/chat/completions",
                        headers=self.headers,
                        json=payload,
                        timeout=self.config['timeout']
                    )

                    if response.status_code == 200:
                        response_data = response.json()
                        
                        if 'choices' in response_data and response_data['choices']:
                            content = response_data['choices'][0]['message']['content']
                            
                            try:
                                parsed_response = json.loads(content)
                                
                                # Validate and enhance response
                                is_valid, errors, corrected_response = self.validator.validate_response(parsed_response)
                                
                                result = {
                                    "raw_analysis": corrected_response,
                                    "model_name": self.model,
                                    "success": True,
                                    "validation_passed": is_valid,
                                    "validation_errors": errors if errors else None,
                                    "text_optimized": len(text) != len(optimized_text),
                                    "provider": "OpenRouter"
                                }
                                
                                if not is_valid:
                                    logger.warning(f"OpenRouter response validation issues: {errors}")
                                
                                return result
                                
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse OpenRouter response: {e}")
                                return {
                                    "success": False,
                                    "error": "Invalid JSON response from OpenRouter",
                                    "model_name": self.model,
                                    "provider": "OpenRouter"
                                }
                        else:
                            logger.error("Empty response from OpenRouter API")
                            return {
                                "success": False,
                                "error": "Empty response from OpenRouter",
                                "model_name": self.model,
                                "provider": "OpenRouter"
                            }
                    
                    elif response.status_code == 429:  # Rate limited
                        if attempt < self.config['max_retries'] - 1:
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                            time.sleep(wait_time)
                            continue
                        else:
                            return {
                                "success": False,
                                "error": "Rate limited by OpenRouter API",
                                "model_name": self.model,
                                "provider": "OpenRouter"
                            }
                    
                    else:
                        error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "error": error_msg,
                            "model_name": self.model,
                            "provider": "OpenRouter"
                        }
                        
                except requests.RequestException as e:
                    if attempt < self.config['max_retries'] - 1:
                        logger.warning(f"Request failed, retrying: {e}")
                        continue
                    else:
                        logger.error(f"OpenRouter request failed after retries: {e}")
                        return {
                            "success": False,
                            "error": f"Request failed: {str(e)}",
                            "model_name": self.model,
                            "provider": "OpenRouter"
                        }

        except Exception as e:
            logger.error(f"Error in OpenRouter analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model,
                "provider": "OpenRouter"
            }