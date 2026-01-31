"""
Direct Anthropic Claude Model Implementation

Provides document analysis using Claude 3.5/3.7 Sonnet via direct Anthropic API.
No OpenRouter middleman - direct integration for optimal performance.
"""

import os
import base64
import json
import logging
from typing import Dict, Any, Optional
from anthropic import Anthropic
from ..models import BaseModel
from . import ModelRegistry
from ...prompt_manager import prompt_manager
from ...response_validator import ResponseValidator

logger = logging.getLogger(__name__)


class ClaudeVisionModel(BaseModel):
    """
    Claude 3.5/3.7 Sonnet vision model via direct Anthropic API.

    Excellent for:
    - Complex document understanding with reasoning
    - Nuanced analysis of business documents
    - High-accuracy structured data extraction
    - Multi-page document analysis

    Models:
    - claude-3-5-sonnet-20241022 (current default)
    - claude-3-7-sonnet-20250219 (future release)
    """

    description = (
        "Claude 3.5/3.7 Sonnet - Direct Anthropic API for premium document analysis"
    )
    requires_env_vars = ["ANTHROPIC_API_KEY"]

    DEFAULT_CONFIG = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "temperature": 0.2,
    }

    def __init__(self):
        """Initialize Claude client with API key from environment."""
        super().__init__()

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = Anthropic(api_key=api_key)
        self.config = self._load_config()
        self.schema = self._load_schema()
        self.validator = ResponseValidator(self.schema)

        logger.info(f"Initialized Claude model: {self.config['model']}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = self.DEFAULT_CONFIG.copy()

        env_mapping = {
            "CLAUDE_MODEL": ("model", str),
            "CLAUDE_MAX_TOKENS": ("max_tokens", int),
            "CLAUDE_TEMPERATURE": ("temperature", float),
        }

        for env_var, (config_key, type_func) in env_mapping.items():
            if value := os.getenv(env_var):
                try:
                    config[config_key] = type_func(value)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid value for {env_var}: {e}")

        return config

    def _load_schema(self) -> dict:
        """Load JSON schema from file."""
        schema_path = os.getenv("DOCFLOW_SCHEMA_PATH", "config/schema.json")
        try:
            with open(schema_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema from {schema_path}: {e}")
            raise

    def _get_instruction_key(self) -> str:
        """Get the model key for prompt instructions."""
        for model_id, model_class in ModelRegistry._models.items():
            if model_class is self.__class__:
                return model_id
        return "claude-vision"

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _get_media_type(self, image_path: str) -> str:
        """Get media type from file extension."""
        extension = os.path.splitext(image_path)[1].lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_types.get(extension, "image/jpeg")

    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract information from text and/or image using Claude.

        Args:
            text: Extracted text content from document
            image_path: Optional path to image for vision analysis

        Returns:
            Dictionary with extraction results
        """
        try:
            # Get model-specific instructions
            model_instructions = prompt_manager.get_model_specific_instructions(
                self._get_instruction_key()
            )

            # Generate enhanced prompt
            prompt = prompt_manager.generate_prompt(
                document_text=text,
                schema=self.schema,
                model_specific_instructions=model_instructions,
            )

            # Prepare message content
            content = []

            # Add text content
            content.append({"type": "text", "text": prompt})

            # Add image if provided
            if image_path:
                try:
                    image_data = self._encode_image(image_path)
                    media_type = self._get_media_type(image_path)
                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        }
                    )
                    logger.debug(f"Added image to Claude request: {image_path}")
                except Exception as e:
                    logger.warning(f"Failed to encode image {image_path}: {e}")

            # Create message
            message = self.client.messages.create(
                model=self.config["model"],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                messages=[{"role": "user", "content": content}],
            )

            # Extract response text
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            # Parse JSON response
            try:
                parsed_response = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                import re

                json_match = re.search(
                    r"```(?:json)?\s*(.*?)\s*```", response_text, re.DOTALL
                )
                if json_match:
                    try:
                        parsed_response = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        parsed_response = {
                            "error": "Invalid JSON",
                            "raw_response": response_text,
                        }
                else:
                    parsed_response = {
                        "error": "Invalid JSON",
                        "raw_response": response_text,
                    }

            # Validate response against schema
            is_valid, errors, corrected_response = self.validator.validate_response(
                parsed_response
            )

            result = {
                "raw_analysis": corrected_response,
                "model_name": self.config["model"],
                "success": True,
                "validation_passed": is_valid,
                "validation_errors": errors if errors else None,
                "provider": "anthropic",
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
            }

            if not is_valid:
                logger.warning(f"Claude response validation issues: {errors}")

            return result

        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.config["model"],
                "provider": "anthropic",
            }

    @classmethod
    def is_available(cls) -> bool:
        """Check if Claude API is available (API key present)."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        available = bool(api_key)
        if available:
            logger.info("Claude model available (API key present)")
        else:
            logger.debug("Claude model unavailable (ANTHROPIC_API_KEY not set)")
        return available

    def get_capabilities(self) -> Dict[str, bool]:
        """Get Claude capabilities."""
        return {
            "vision": True,
            "multilingual": True,
            "streaming": False,  # Can be enabled later
            "structured_output": True,
            "long_context": True,
            "reasoning": True,
        }


# Register the model
ModelRegistry.register("claude-vision", ClaudeVisionModel)
logger.info("Registered claude-vision model (direct Anthropic API)")
