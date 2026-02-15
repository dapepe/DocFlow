"""
Claude Vision Model Implementation

Direct integration with Anthropic Claude API for high-performance vision analysis.
Uses the official Anthropic Python SDK.
"""

import os
import base64
import json
import structlog
from typing import Dict, Any, Optional, List
from pathlib import Path
from docflow.models.providers.base import BaseProvider
from docflow.prompt_manager import prompt_manager
from docflow.response_validator import ResponseValidator

logger = structlog.get_logger(__name__)


class ClaudeVisionModel(BaseProvider):
    """
    Direct integration with Anthropic Claude 3.7 Sonnet (and others) via SDK.

    Excellent for:
    - Complex reasoning and document analysis
    - Nuanced visual understanding
    - Structured data extraction
    - High accuracy requirements
    """

    description = "Claude 3.7 Sonnet (API) - Advanced reasoning and vision model"
    requires_env_vars = ["ANTHROPIC_API_KEY"]

    # Default configuration
    DEFAULT_CONFIG = {
        "model": "claude-3-7-sonnet-20250219",  # Latest model
        "max_tokens": 4096,
        "temperature": 0.0,
        "timeout": 60.0,
        "max_retries": 3,
    }

    def __init__(self):
        """Initialize Claude model with API client."""
        super().__init__()
        self.config = self._load_config()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None  # Lazy initialization
        self.async_client = None  # Lazy initialization

        self.schema = self._load_schema()
        self.validator = ResponseValidator(self.schema)

        # Set capabilities
        self.capabilities.vision = True
        self.capabilities.multilingual = True
        self.capabilities.structured_output = True
        self.capabilities.reasoning = True
        self.capabilities.long_context = True  # Claude has 200k context

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = self.DEFAULT_CONFIG.copy()

        if model := os.getenv("CLAUDE_MODEL"):
            config["model"] = model

        if max_tokens := os.getenv("CLAUDE_MAX_TOKENS"):
            try:
                config["max_tokens"] = int(max_tokens)
            except ValueError:
                pass

        if temp := os.getenv("CLAUDE_TEMPERATURE"):
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

    def _ensure_client(self):
        """Initialize Anthropic client if not already done."""
        if not self.client:
            try:
                from anthropic import Anthropic

                if not self.api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable not set")

                self.client = Anthropic(
                    api_key=self.api_key,
                    max_retries=self.config["max_retries"],
                    timeout=self.config["timeout"],
                )
                logger.info("anthropic_client_initialized", model=self.config["model"])
            except ImportError:
                logger.error(
                    "anthropic_sdk_missing",
                    message="Install with: pip install anthropic",
                )
                raise RuntimeError("anthropic package is required")
            except Exception as e:
                logger.error("anthropic_client_init_failed", error=str(e))
                raise

    async def _ensure_async_client(self):
        """Initialize AsyncAnthropic client if not already done."""
        if not self.async_client:
            try:
                from anthropic import AsyncAnthropic

                if not self.api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable not set")

                self.async_client = AsyncAnthropic(
                    api_key=self.api_key,
                    max_retries=self.config["max_retries"],
                    timeout=self.config["timeout"],
                )
                logger.info(
                    "async_anthropic_client_initialized", model=self.config["model"]
                )
            except ImportError:
                logger.error(
                    "anthropic_sdk_missing",
                    message="Install with: pip install anthropic",
                )
                raise RuntimeError("anthropic package is required")
            except Exception as e:
                logger.error("async_anthropic_client_init_failed", error=str(e))
                raise

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _get_media_type(self, image_path: str) -> str:
        """Get media type for image."""
        suffix = Path(image_path).suffix.lower()
        if suffix in [".jpg", ".jpeg"]:
            return "image/jpeg"
        elif suffix == ".png":
            return "image/png"
        elif suffix == ".webp":
            return "image/webp"
        elif suffix == ".gif":
            return "image/gif"
        else:
            return "image/jpeg"  # Default

    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate text from Claude."""
        self._ensure_client()

        temp = temperature if temperature is not None else self.config["temperature"]
        max_tok = max_tokens if max_tokens is not None else self.config["max_tokens"]

        try:
            messages = []
            content = []

            # Add images if provided
            # Note: The images arg in BaseProvider is list of base64 strings
            # But here we might need media type.
            # For simplicity, we assume JPEG if passed as raw base64 strings without context.
            # But extract_information passes image_path, so we handle that better there.

            if images:
                for img_b64 in images:
                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",  # Assumption
                                "data": img_b64,
                            },
                        }
                    )

            content.append({"type": "text", "text": prompt})
            messages.append({"role": "user", "content": content})

            response = self.client.messages.create(
                model=self.config["model"],
                max_tokens=max_tok,
                temperature=temp,
                messages=messages,
            )

            return response.content[0].text

        except Exception as e:
            logger.error("claude_generation_failed", error=str(e))
            raise

    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information using Claude."""
        self._ensure_client()

        try:
            # Prepare prompt
            prompt = prompt_manager.generate_prompt(
                document_text=text,
                schema=self.schema,
                model_specific_instructions=prompt_manager.get_model_specific_instructions(
                    "claude-vision"
                ),
            )

            messages = []
            content = []

            # Handle image
            if image_path:
                try:
                    img_b64 = self._encode_image(image_path)
                    media_type = self._get_media_type(image_path)
                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_b64,
                            },
                        }
                    )
                    logger.debug(
                        "image_attached_to_request",
                        path=image_path,
                        media_type=media_type,
                    )
                except Exception as e:
                    logger.warning("image_attachment_failed", error=str(e))

            content.append({"type": "text", "text": prompt})
            messages.append({"role": "user", "content": content})

            # Make API call
            logger.info("calling_claude_api", model=self.config["model"])
            response = self.client.messages.create(
                model=self.config["model"],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                messages=messages,
            )

            response_text = response.content[0].text

            # Parse JSON
            try:
                # Find JSON block
                import re

                json_match = re.search(
                    r"```(?:json)?\s*(.*?)\s*```", response_text, re.DOTALL
                )
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response_text

                parsed_response = json.loads(json_str)

            except json.JSONDecodeError:
                logger.warning(
                    "json_parsing_failed", response_snippet=response_text[:100]
                )
                return {
                    "success": False,
                    "error": "Invalid JSON response",
                    "raw_response": response_text,
                    "model_name": self.config["model"],
                    "provider": "anthropic",
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
                "provider": "anthropic",
            }

        except Exception as e:
            logger.error("claude_extraction_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "model_name": self.config["model"],
                "provider": "anthropic",
            }

    async def extract_information_async(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Async version of extraction."""
        await self._ensure_async_client()

        try:
            # Prepare prompt
            prompt = prompt_manager.generate_prompt(
                document_text=text,
                schema=self.schema,
                model_specific_instructions=prompt_manager.get_model_specific_instructions(
                    "claude-vision"
                ),
            )

            messages = []
            content = []

            # Handle image
            if image_path:
                try:
                    # Run file IO in thread pool
                    import asyncio

                    loop = asyncio.get_event_loop()
                    img_b64 = await loop.run_in_executor(
                        None, self._encode_image, image_path
                    )
                    media_type = self._get_media_type(image_path)

                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_b64,
                            },
                        }
                    )
                except Exception as e:
                    logger.warning("image_attachment_failed_async", error=str(e))

            content.append({"type": "text", "text": prompt})
            messages.append({"role": "user", "content": content})

            # Make Async API call
            logger.info("calling_claude_api_async", model=self.config["model"])
            response = await self.async_client.messages.create(
                model=self.config["model"],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                messages=messages,
            )

            response_text = response.content[0].text

            # Parse JSON (reuse sync logic or duplicate)
            try:
                import re

                json_match = re.search(
                    r"```(?:json)?\s*(.*?)\s*```", response_text, re.DOTALL
                )
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response_text

                parsed_response = json.loads(json_str)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON response",
                    "raw_response": response_text,
                    "model_name": self.config["model"],
                    "provider": "anthropic",
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
                "provider": "anthropic",
            }

        except Exception as e:
            logger.error("claude_extraction_async_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "model_name": self.config["model"],
                "provider": "anthropic",
            }

    @classmethod
    def is_available(cls) -> bool:
        """Check if API key is set."""
        return bool(os.getenv("ANTHROPIC_API_KEY"))


# Register
from docflow.models import ModelRegistry

ModelRegistry.register("claude-vision", ClaudeVisionModel)
