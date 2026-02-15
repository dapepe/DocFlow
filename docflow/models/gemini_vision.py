"""
Gemini Vision Model Implementation

Direct integration with Google Gemini API for fast, multimodal document processing.
Uses the official google-generativeai Python SDK.
"""

import os
import json
import structlog
from typing import Dict, Any, Optional, List
from pathlib import Path
from docflow.models.providers.base import BaseProvider
from docflow.prompt_manager import prompt_manager
from docflow.response_validator import ResponseValidator

logger = structlog.get_logger(__name__)


class GeminiVisionModel(BaseProvider):
    """
    Direct integration with Google Gemini 2.0 Flash/Pro via SDK.

    Excellent for:
    - Fast processing (Flash is very fast)
    - Long context windows (1M+ tokens)
    - Native JSON output mode
    - Multimodal understanding
    """

    description = "Gemini 2.0 Flash (API) - Ultra-fast multimodal model"
    requires_env_vars = ["GOOGLE_API_KEY"]

    # Default configuration
    DEFAULT_CONFIG = {
        "model": "gemini-2.0-flash",
        "max_tokens": 8192,
        "temperature": 0.1,
    }

    def __init__(self):
        """Initialize Gemini model with API client."""
        super().__init__()
        self.config = self._load_config()
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_instance = None  # Lazy initialization

        self.schema = self._load_schema()
        self.validator = ResponseValidator(self.schema)

        # Set capabilities
        self.capabilities.vision = True
        self.capabilities.multilingual = True
        self.capabilities.structured_output = True
        self.capabilities.long_context = True
        self.capabilities.fast = True  # Flash is fast

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = self.DEFAULT_CONFIG.copy()

        if model := os.getenv("GEMINI_MODEL"):
            config["model"] = model

        if max_tokens := os.getenv("GEMINI_MAX_TOKENS"):
            try:
                config["max_tokens"] = int(max_tokens)
            except ValueError:
                pass

        if temp := os.getenv("GEMINI_TEMPERATURE"):
            try:
                config["temperature"] = float(temp)
            except ValueError:
                pass

        return config

    def _load_schema(self) -> dict:
        """Load JSON schema from file."""
        schema_path = os.getenv("DOCFLOW_SCHEMA_PATH", "config/schema.json")
        try:
            with open(schema_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("schema_load_failed", schema_path=schema_path, error=str(e))
            raise

    def _ensure_model(self):
        """Initialize GenerativeModel if not already done."""
        if not self.model_instance:
            try:
                import google.generativeai as genai

                if not self.api_key:
                    raise ValueError("GOOGLE_API_KEY environment variable not set")

                genai.configure(api_key=self.api_key)

                self.model_instance = genai.GenerativeModel(
                    model_name=self.config["model"],
                    generation_config={
                        "temperature": self.config["temperature"],
                        "max_output_tokens": self.config["max_tokens"],
                        "response_mime_type": "application/json",  # Enforce JSON
                    },
                )
                logger.info("gemini_model_initialized", model=self.config["model"])
            except ImportError:
                logger.error(
                    "google_genai_sdk_missing",
                    message="Install with: pip install google-generativeai",
                )
                raise RuntimeError("google-generativeai package is required")
            except Exception as e:
                logger.error("gemini_model_init_failed", error=str(e))
                raise

    def _load_image(self, image_path: str):
        """Load image as PIL Image for Gemini."""
        from PIL import Image

        return Image.open(image_path)

    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate text from Gemini."""
        self._ensure_model()

        try:
            content = [prompt]

            # Note: images here are base64 strings from BaseProvider interface
            # Gemini prefers PIL images or File API.
            # Convert base64 back to PIL? Or use file path if available (via extract_information)
            # generate() only gets base64.

            if images:
                import io
                from PIL import Image

                for img_b64 in images:
                    img_data = base64.b64decode(img_b64)
                    img = Image.open(io.BytesIO(img_data))
                    content.append(img)

            # Override generation config if params provided
            generation_config = None
            if temperature is not None or max_tokens is not None:
                generation_config = {
                    "temperature": temperature
                    if temperature is not None
                    else self.config["temperature"],
                    "max_output_tokens": max_tokens
                    if max_tokens is not None
                    else self.config["max_tokens"],
                }

            response = self.model_instance.generate_content(
                content, generation_config=generation_config
            )

            return response.text

        except Exception as e:
            logger.error("gemini_generation_failed", error=str(e))
            raise

    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information using Gemini."""
        self._ensure_model()

        try:
            # Prepare prompt
            prompt = prompt_manager.generate_prompt(
                document_text=text,
                schema=self.schema,
                model_specific_instructions=prompt_manager.get_model_specific_instructions(
                    "gemini-vision"
                ),
            )

            content = [prompt]

            # Handle image
            if image_path:
                try:
                    img = self._load_image(image_path)
                    content.append(img)
                    logger.debug("image_attached_to_request", path=image_path)
                except Exception as e:
                    logger.warning("image_attachment_failed", error=str(e))

            # Make API call
            logger.info("calling_gemini_api", model=self.config["model"])

            # Gemini Native JSON mode
            # We already configured response_mime_type="application/json" in _ensure_model
            # But prompt template also asks for JSON.

            response = self.model_instance.generate_content(content)
            response_text = response.text

            # Parse JSON
            try:
                parsed_response = json.loads(response_text)
            except json.JSONDecodeError:
                # Even with JSON mode, sometimes it might wrap or fail
                parsed_response = {
                    "error": "Invalid JSON response",
                    "raw_response": response_text,
                    "model_name": self.config["model"],
                    "provider": "google",
                }

            # Validate
            is_valid, errors, corrected_response = self.validator.validate_response(
                parsed_response
            )

            return {
                "raw_analysis": corrected_response,
                "model_name": self.config["model"],
                "success": True,
                "validation_passed": is_valid,
                "validation_errors": errors,
                "provider": "google",
            }

        except Exception as e:
            logger.error("gemini_extraction_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "model_name": self.config["model"],
                "provider": "google",
            }

    async def extract_information_async(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Async version of extraction."""
        self._ensure_model()

        try:
            # Prepare prompt
            prompt = prompt_manager.generate_prompt(
                document_text=text,
                schema=self.schema,
                model_specific_instructions=prompt_manager.get_model_specific_instructions(
                    "gemini-vision"
                ),
            )

            content = [prompt]

            if image_path:
                # Load image in thread pool
                import asyncio

                loop = asyncio.get_event_loop()
                try:
                    img = await loop.run_in_executor(None, self._load_image, image_path)
                    content.append(img)
                except Exception as e:
                    logger.warning("image_attachment_failed_async", error=str(e))

            logger.info("calling_gemini_api_async", model=self.config["model"])

            # Use async generate_content
            response = await self.model_instance.generate_content_async(content)
            response_text = response.text

            try:
                parsed_response = json.loads(response_text)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON response",
                    "raw_response": response_text,
                    "model_name": self.config["model"],
                    "provider": "google",
                }

            is_valid, errors, corrected_response = self.validator.validate_response(
                parsed_response
            )

            return {
                "raw_analysis": corrected_response,
                "model_name": self.config["model"],
                "success": True,
                "validation_passed": is_valid,
                "validation_errors": errors,
                "provider": "google",
            }

        except Exception as e:
            logger.error("gemini_extraction_async_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "model_name": self.config["model"],
                "provider": "google",
            }

    @classmethod
    def is_available(cls) -> bool:
        """Check if API key is set."""
        return bool(os.getenv("GOOGLE_API_KEY"))


# Register
from docflow.models import ModelRegistry

ModelRegistry.register("gemini-vision", GeminiVisionModel)
