"""
OpenRouter Base Model Implementation
Provides shared functionality for OpenRouter-based vision models
"""

import os
import json
import base64
import structlog
from typing import Dict, Any, Optional, List
from .providers.base import HTTPProvider
from ..settings import settings
from ..prompt_manager import prompt_manager
from ..response_validator import ResponseValidator
from ..performance_optimizer import (
    cached_model_response,
    cached_model_response_async,
    optimize_text_extraction,
)

logger = structlog.get_logger(__name__)


class OpenRouterBaseModel(HTTPProvider):
    """Base class for OpenRouter-based vision models"""

    description = "Base OpenRouter Vision Model"
    requires_env_vars = ["OPENROUTER_API_KEY"]

    def __init__(self):
        """Initialize the model with configuration from environment"""
        super().__init__()  # Initialize HTTPProvider (loads config + session)
        self.model = self._get_model_name()
        self.schema = self._load_schema()
        self.validator = ResponseValidator(self.schema)

        # Enable vision and structured output capabilities
        self.capabilities.vision = True
        self.capabilities.structured_output = True

        logger.info("openrouter_model_initialized", model_name=self.model)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from centralized settings"""
        return {
            "api_base": settings.openrouter_api_base,
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
            "timeout": settings.openrouter_timeout,
            "max_retries": settings.openrouter_max_retries,
        }

    def _setup_headers(self) -> Dict[str, str]:
        """Setup API request headers"""
        return {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_app_name,
        }

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the model name. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _get_model_name")

    @classmethod
    def is_available(cls) -> bool:
        """Check if OpenRouter API is available"""
        if not settings.openrouter_api_key:
            return False
        return True

    def _load_schema(self) -> dict:
        """Load JSON schema from file"""
        schema_path = os.getenv("DOCFLOW_SCHEMA_PATH", "config/schema.json")
        try:
            with open(schema_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("schema_load_failed", schema_path=schema_path, error=str(e))
            raise

    def _generate_enhanced_prompt(
        self,
        text: str,
        document_type: Optional[str] = None,
        file_extension: Optional[str] = None,
    ) -> str:
        """Generate an enhanced prompt using the configurable prompt system"""
        model_instructions = prompt_manager.get_model_specific_instructions(
            self._get_model_key()
        )

        return prompt_manager.generate_prompt(
            document_text=text,
            schema=self.schema,
            document_type=document_type,
            file_extension=file_extension,
            model_specific_instructions=model_instructions,
        )

    def _get_model_key(self) -> str:
        """Get the model key for prompt instructions"""
        return (
            self.__class__.__name__.lower()
            .replace("model", "")
            .replace("openrouter", "")
        )

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _get_image_mime_type(self, image_path: str) -> str:
        """Get MIME type from image file extension"""
        extension = os.path.splitext(image_path)[1].lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_types.get(extension, "image/jpeg")

    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Implement abstract generate method"""
        return ""

    @cached_model_response
    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information from text and/or image using OpenRouter"""
        try:
            # Optimize text for processing
            optimized_text = optimize_text_extraction(text)
            prompt = self._generate_enhanced_prompt(optimized_text)

            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert document analysis AI with advanced OCR and information extraction capabilities.",
                }
            ]

            # Prepare content parts
            content_parts = [{"type": "text", "text": prompt}]

            # Add image if available
            if image_path:
                base64_image = self._encode_image(image_path)
                mime_type = self._get_image_mime_type(image_path)
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "high",
                        },
                    }
                )

            messages.append({"role": "user", "content": content_parts})

            # Prepare API request
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.config["max_tokens"],
                "temperature": self.config["temperature"],
                "response_format": {"type": "json_object"},
            }

            # Use HTTPProvider's _make_request which handles retries and session pooling
            response_data = self._make_request(
                method="POST",
                url=f"{self.config['api_base']}/chat/completions",
                json_data=payload,
            )

            if "choices" in response_data and response_data["choices"]:
                content = response_data["choices"][0]["message"]["content"]

                try:
                    parsed_response = json.loads(content)

                    # Validate and enhance response
                    is_valid, errors, corrected_response = (
                        self.validator.validate_response(parsed_response)
                    )

                    result = {
                        "raw_analysis": corrected_response,
                        "model_name": self.model,
                        "success": True,
                        "validation_passed": is_valid,
                        "validation_errors": errors if errors else None,
                        "text_optimized": len(text) != len(optimized_text),
                        "provider": "OpenRouter",
                    }

                    if not is_valid:
                        logger.warning(
                            "openrouter_validation_failed", validation_errors=errors
                        )

                    return result

                except json.JSONDecodeError as e:
                    logger.error("openrouter_json_parse_failed", error=str(e))
                    return {
                        "success": False,
                        "error": "Invalid JSON response from OpenRouter",
                        "model_name": self.model,
                        "provider": "OpenRouter",
                    }
            else:
                logger.error("openrouter_empty_response")
                return {
                    "success": False,
                    "error": "Empty response from OpenRouter",
                    "model_name": self.model,
                    "provider": "OpenRouter",
                }

        except Exception as e:
            logger.error("openrouter_analysis_error", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model,
                "provider": "OpenRouter",
            }

    @cached_model_response_async
    async def extract_information_async(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information from text and/or image using OpenRouter (Async)"""
        try:
            # Optimize text for processing
            optimized_text = optimize_text_extraction(text)
            prompt = self._generate_enhanced_prompt(optimized_text)

            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert document analysis AI with advanced OCR and information extraction capabilities.",
                }
            ]

            # Prepare content parts
            content_parts = [{"type": "text", "text": prompt}]

            # Add image if available
            if image_path:
                base64_image = self._encode_image(image_path)
                mime_type = self._get_image_mime_type(image_path)
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "high",
                        },
                    }
                )

            messages.append({"role": "user", "content": content_parts})

            # Prepare API request
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.config["max_tokens"],
                "temperature": self.config["temperature"],
                "response_format": {"type": "json_object"},
            }

            # Use HTTPProvider's _make_request_async
            response_data = await self._make_request_async(
                method="POST",
                url=f"{self.config['api_base']}/chat/completions",
                json_data=payload,
            )

            if "choices" in response_data and response_data["choices"]:
                content = response_data["choices"][0]["message"]["content"]

                try:
                    parsed_response = json.loads(content)

                    # Validate and enhance response
                    is_valid, errors, corrected_response = (
                        self.validator.validate_response(parsed_response)
                    )

                    result = {
                        "raw_analysis": corrected_response,
                        "model_name": self.model,
                        "success": True,
                        "validation_passed": is_valid,
                        "validation_errors": errors if errors else None,
                        "text_optimized": len(text) != len(optimized_text),
                        "provider": "OpenRouter",
                    }

                    if not is_valid:
                        logger.warning(
                            "openrouter_validation_failed", validation_errors=errors
                        )

                    return result

                except json.JSONDecodeError as e:
                    logger.error("openrouter_json_parse_failed", error=str(e))
                    return {
                        "success": False,
                        "error": "Invalid JSON response from OpenRouter",
                        "model_name": self.model,
                        "provider": "OpenRouter",
                    }
            else:
                logger.error("openrouter_empty_response")
                return {
                    "success": False,
                    "error": "Empty response from OpenRouter",
                    "model_name": self.model,
                    "provider": "OpenRouter",
                }

        except Exception as e:
            logger.error("openrouter_analysis_error", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model,
                "provider": "OpenRouter",
            }
