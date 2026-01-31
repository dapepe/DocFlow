"""
Direct Google Gemini Model Implementation

Provides document analysis using Gemini 2.0 Flash/Pro via direct Google API.
Fast multimodal processing with native JSON mode support.
"""

import os
import base64
import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from ..models import BaseModel
from . import ModelRegistry
from ...prompt_manager import prompt_manager
from ...response_validator import ResponseValidator

logger = logging.getLogger(__name__)


class GeminiVisionModel(BaseModel):
    """
    Gemini 2.0 Flash/Pro vision model via direct Google API.

    Excellent for:
    - Fast document processing (Flash)
    - High-quality analysis (Pro)
    - Multilingual document understanding
    - Native JSON structured output

    Models:
    - gemini-2.0-flash-exp (fast, cost-effective)
    - gemini-2.0-pro-exp (highest quality)
    - gemini-1.5-flash (stable)
    - gemini-1.5-pro (stable)
    """

    description = (
        "Gemini 2.0 Flash/Pro - Direct Google API for fast multimodal processing"
    )
    requires_env_vars = ["GOOGLE_API_KEY"]

    DEFAULT_CONFIG = {
        "model": "gemini-2.0-flash-exp",
        "temperature": 0.2,
        "max_output_tokens": 4096,
    }

    def __init__(self):
        """Initialize Gemini client with API key from environment."""
        super().__init__()

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")

        # Configure the Gemini API
        genai.configure(api_key=api_key)

        self.config = self._load_config()
        self.schema = self._load_schema()
        self.validator = ResponseValidator(self.schema)

        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=self.config["model"],
            generation_config={
                "temperature": self.config["temperature"],
                "max_output_tokens": self.config["max_output_tokens"],
                "response_mime_type": "application/json",
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )

        logger.info(f"Initialized Gemini model: {self.config['model']}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = self.DEFAULT_CONFIG.copy()

        env_mapping = {
            "GEMINI_MODEL": ("model", str),
            "GEMINI_MAX_TOKENS": ("max_output_tokens", int),
            "GEMINI_TEMPERATURE": ("temperature", float),
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
        return "gemini-vision"

    def _encode_image(self, image_path: str) -> bytes:
        """Read and return image bytes."""
        with open(image_path, "rb") as image_file:
            return image_file.read()

    def _get_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension."""
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
        Extract information from text and/or image using Gemini.

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

            # Prepare content
            content = [prompt]

            # Add image if provided
            if image_path:
                try:
                    image_bytes = self._encode_image(image_path)
                    mime_type = self._get_mime_type(image_path)

                    # Create image part
                    image_part = {"mime_type": mime_type, "data": image_bytes}
                    content.append(image_part)

                    logger.debug(f"Added image to Gemini request: {image_path}")
                except Exception as e:
                    logger.warning(f"Failed to encode image {image_path}: {e}")

            # Generate response
            response = self.model.generate_content(content)

            # Extract response text
            response_text = response.text

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
                "provider": "google",
            }

            # Add usage metadata if available
            if hasattr(response, "usage_metadata"):
                result["usage"] = {
                    "prompt_tokens": getattr(
                        response.usage_metadata, "prompt_token_count", 0
                    ),
                    "completion_tokens": getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    ),
                    "total_tokens": getattr(
                        response.usage_metadata, "total_token_count", 0
                    ),
                }

            if not is_valid:
                logger.warning(f"Gemini response validation issues: {errors}")

            return result

        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.config["model"],
                "provider": "google",
            }

    @classmethod
    def is_available(cls) -> bool:
        """Check if Gemini API is available (API key present)."""
        api_key = os.getenv("GOOGLE_API_KEY")
        available = bool(api_key)
        if available:
            logger.info("Gemini model available (API key present)")
        else:
            logger.debug("Gemini model unavailable (GOOGLE_API_KEY not set)")
        return available

    def get_capabilities(self) -> Dict[str, bool]:
        """Get Gemini capabilities."""
        return {
            "vision": True,
            "multilingual": True,
            "streaming": True,  # Gemini supports streaming
            "structured_output": True,  # Native JSON mode
            "fast": "flash" in self.config["model"],
            "pro": "pro" in self.config["model"],
        }


# Register the model
ModelRegistry.register("gemini-vision", GeminiVisionModel)
logger.info("Registered gemini-vision model (direct Google API)")
