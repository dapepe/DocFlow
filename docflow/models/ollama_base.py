"""
Base Ollama Model Implementation
Provides shared functionality for Ollama-based models
"""

import os
import json
import re
import logging
import requests
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

logger = logging.getLogger(__name__)


class OllamaBaseModel(HTTPProvider):
    """Base class for Ollama-based models"""

    description = "Base Ollama Model"
    requires_env_vars = []  # No required env vars since we have defaults

    def __init__(self):
        """Initialize the model with configuration from environment"""
        super().__init__()  # Initialize HTTPProvider
        self.model = self._get_model_name()
        self.schema = self._load_schema()
        self.validator = ResponseValidator(self.schema)

        # Enable capabilities
        self.capabilities.local = True
        self.capabilities.structured_output = True

        logger.info(f"Initialized Ollama model: {self.model}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from centralized settings"""
        return {
            "host": settings.ollama_host,
            "temperature": settings.temperature,
            "timeout": settings.ollama_timeout,
            "max_retries": settings.ollama_max_retries,
            "retry_backoff": settings.ollama_retry_backoff,
        }

    def _setup_headers(self) -> Dict[str, str]:
        """Setup API request headers (minimal for Ollama)"""
        return {"Content-Type": "application/json"}

    @classmethod
    def _get_model_name(cls) -> str:
        """Get the model name with proper format. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _get_model_name")

    @classmethod
    def is_available(cls) -> bool:
        """Check if Ollama service is available and the required model is installed"""
        try:
            # Simple check first
            response = requests.get(f"{settings.ollama_host}/api/tags", timeout=5)

            if response.status_code == 200:
                models = response.json().get("models", [])
                required_model = cls._get_model_name()
                base_model = required_model.split(":")[0]

                available_models = [m.get("name", "") for m in models]

                # Check if any model starts with our base model name
                return any(m.startswith(base_model) for m in available_models)

            return False

        except Exception:
            return False

    def _load_schema(self) -> dict:
        """Load JSON schema from file"""
        schema_path = os.getenv("DOCFLOW_SCHEMA_PATH", "config/schema.json")
        try:
            with open(schema_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema from {schema_path}: {e}")
            raise

    def _generate_enhanced_prompt(
        self,
        text: str,
        document_type: Optional[str] = None,
        file_extension: Optional[str] = None,
    ) -> str:
        """Generate an enhanced prompt using the configurable prompt system"""
        model_instructions = prompt_manager.get_model_specific_instructions(
            self.__class__.__name__.replace("Model", "")
            .lower()
            .replace("ollama", "")
            .replace("base", "")
        )

        return prompt_manager.generate_prompt(
            document_text=text,
            schema=self.schema,
            document_type=document_type,
            file_extension=file_extension,
            model_specific_instructions=model_instructions,
        )

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

    def _repair_json(self, json_str: str) -> Dict[str, Any]:
        """Attempt to repair malformed JSON from LLM output"""
        try:
            # First try parsing as-is
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                # Cleanup common issues
                fixed = json_str.strip()

                # Extract JSON block if embedded in markdown
                if "```json" in fixed:
                    fixed = fixed.split("```json")[1].split("```")[0].strip()
                elif "```" in fixed:
                    fixed = fixed.split("```")[1].split("```")[0].strip()

                # Fix trailing commas
                fixed = re.sub(r",\s*}", "}", fixed)
                fixed = re.sub(r",\s*]", "]", fixed)

                # Quote unquoted keys
                fixed = re.sub(
                    r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', fixed
                )

                return json.loads(fixed)
            except Exception:
                return {"error": "Failed to parse JSON", "raw": json_str}

    @cached_model_response
    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information from text and/or image using Ollama"""
        try:
            # Optimize text for processing
            optimized_text = optimize_text_extraction(text)
            prompt = self._generate_enhanced_prompt(optimized_text)

            payload = {
                "model": self.model,
                "prompt": prompt,
                "format": "json",  # Ollama supports JSON mode natively now
                "stream": False,
                "options": {"temperature": self.config["temperature"]},
            }

            # Use HTTPProvider's _make_request
            response_data = self._make_request(
                method="POST",
                url=f"{self.config['host']}/api/generate",
                json_data=payload,
            )

            response_text = response_data.get("response", "")
            parsed_response = self._repair_json(response_text)

            # Validate response
            is_valid, errors, corrected_response = self.validator.validate_response(
                parsed_response
            )

            result = {
                "raw_analysis": corrected_response,
                "model_name": self.model,
                "success": True,
                "validation_passed": is_valid,
                "validation_errors": errors if errors else None,
                "text_optimized": len(text) != len(optimized_text),
                "provider": "Ollama",
            }

            if not is_valid:
                logger.warning(f"Ollama response validation issues: {errors}")

            return result

        except Exception as e:
            logger.error(f"Error in Ollama analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model,
                "provider": "Ollama",
            }

    @cached_model_response_async
    async def extract_information_async(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information from text and/or image using Ollama (Async)"""
        try:
            # Optimize text for processing
            optimized_text = optimize_text_extraction(text)
            prompt = self._generate_enhanced_prompt(optimized_text)

            payload = {
                "model": self.model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": self.config["temperature"]},
            }

            # Use HTTPProvider's _make_request_async
            response_data = await self._make_request_async(
                method="POST",
                url=f"{self.config['host']}/api/generate",
                json_data=payload,
            )

            response_text = response_data.get("response", "")
            parsed_response = self._repair_json(response_text)

            # Validate response
            is_valid, errors, corrected_response = self.validator.validate_response(
                parsed_response
            )

            result = {
                "raw_analysis": corrected_response,
                "model_name": self.model,
                "success": True,
                "validation_passed": is_valid,
                "validation_errors": errors if errors else None,
                "text_optimized": len(text) != len(optimized_text),
                "provider": "Ollama",
            }

            if not is_valid:
                logger.warning(f"Ollama response validation issues: {errors}")

            return result

        except Exception as e:
            logger.error(f"Error in Ollama analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": self.model,
                "provider": "Ollama",
            }
