"""
Llama.cpp Provider Implementation

Provides direct GGUF model inference using llama-cpp-python.
Offers lower overhead than Ollama HTTP API with full hardware control.
"""

import os
import base64
import json
import structlog
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from .base import LocalProvider
from ...prompt_manager import prompt_manager
from ...response_validator import ResponseValidator
from . import quantization

logger = structlog.get_logger(__name__)


class LlamaCppProvider(LocalProvider):
    """
    Base provider for llama.cpp GGUF models.

    Loads models directly via llama-cpp-python for optimal performance.
    Supports both text-only and multimodal (vision) models.
    """

    description = "Base llama.cpp GGUF Model Provider"
    requires_env_vars = []  # Optional - can work with default paths

    # Default configuration
    DEFAULT_CONFIG = {
        "n_ctx": 8192,
        "n_threads": None,  # None = auto-detect (os.cpu_count())
        "n_gpu_layers": 0,  # 0 = CPU only, -1 = all layers on GPU
        "verbose": False,
        "chat_format": "chatml",
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    def __init__(self):
        """Initialize the llama.cpp provider with configuration from environment."""
        super().__init__()
        self.config = self._load_config()
        self.model_path = self._get_model_path()
        # self.model is managed by LocalProvider base class
        self.schema = self._load_schema()
        self.validator = ResponseValidator(self.schema)

        logger.info("llama_cpp_provider_initialized", model_path=self.model_path)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables with defaults."""
        config = self.DEFAULT_CONFIG.copy()

        env_mapping = {
            "LLAMA_CPP_N_CTX": ("n_ctx", int),
            "LLAMA_CPP_N_THREADS": ("n_threads", lambda x: int(x) if x else None),
            "LLAMA_CPP_N_GPU_LAYERS": ("n_gpu_layers", int),
            "LLAMA_CPP_VERBOSE": (
                "verbose",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            "LLAMA_CPP_TEMPERATURE": ("temperature", float),
            "LLAMA_CPP_MAX_TOKENS": ("max_tokens", int),
        }

        # Check for auto-GPU configuration
        if os.getenv("LLAMA_CPP_AUTO_GPU_LAYERS", "").lower() in ("true", "1", "yes"):
            try:
                # Get model path (might not be available yet if called from __init__ before subclass init?)
                # Wait, _load_config is called in __init__. _get_model_path is a classmethod.
                # So we can call it.
                model_path = self._get_model_path()
                if model_path and os.path.exists(model_path):
                    vram_gb, ram_gb = quantization.detect_available_vram()
                    logger.info(
                        "auto_gpu_config_detection",
                        vram_gb=vram_gb,
                        ram_gb=ram_gb,
                        model_path=model_path,
                    )

                    if vram_gb > 0:
                        layers = quantization.estimate_gpu_layers(model_path, vram_gb)
                        config["n_gpu_layers"] = layers
                        logger.info(
                            "auto_gpu_layers_set",
                            layers=layers,
                            reason=f"Available VRAM: {vram_gb:.2f} GB",
                        )
                    else:
                        logger.info("no_gpu_detected_using_cpu")
                        config["n_gpu_layers"] = 0
            except Exception as e:
                logger.warning("auto_gpu_config_failed", error=str(e))

        for env_var, (config_key, type_func) in env_mapping.items():
            if value := os.getenv(env_var):
                try:
                    config[config_key] = type_func(value)
                    logger.debug(
                        "llama_cpp_config_loaded",
                        config_key=config_key,
                        value=config[config_key],
                        env_var=env_var,
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "llama_cpp_invalid_config", env_var=env_var, error=str(e)
                    )

        return config

    @classmethod
    def _get_model_path(cls) -> str:
        """Get the GGUF model path. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _get_model_path()")

    def _load_model(self) -> Any:
        """Load the GGUF model using llama-cpp-python."""
        try:
            from llama_cpp import Llama
        except ImportError:
            logger.error(
                "llama_cpp_python_not_installed",
                message="Install with: pip install llama-cpp-python",
            )
            raise RuntimeError("llama-cpp-python is required for GGUF models")

        if not self.model_path or not Path(self.model_path).exists():
            raise FileNotFoundError(f"GGUF model not found: {self.model_path}")

        n_threads = self.config["n_threads"] or os.cpu_count()

        logger.info("llama_cpp_model_loading", model_path=self.model_path)
        logger.info(
            "llama_cpp_config",
            n_ctx=self.config["n_ctx"],
            n_threads=n_threads,
            n_gpu_layers=self.config["n_gpu_layers"],
        )

        try:
            llm = Llama(
                model_path=self.model_path,
                n_ctx=self.config["n_ctx"],
                n_threads=n_threads,
                n_gpu_layers=self.config["n_gpu_layers"],
                verbose=self.config["verbose"],
                chat_format=self.config["chat_format"],
            )
            logger.info("llama_cpp_model_loaded", model_path=self.model_path)
            return llm
        except Exception as e:
            logger.error("llama_cpp_model_load_failed", error=str(e))
            raise RuntimeError(f"Model loading failed: {e}")

    def _load_schema(self) -> dict:
        """Load JSON schema from file."""
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
        """Generate an enhanced prompt using the configurable prompt system."""
        model_instructions = prompt_manager.get_model_specific_instructions(
            self._get_instruction_key()
        )

        return prompt_manager.generate_prompt(
            document_text=text,
            schema=self.schema,
            document_type=document_type,
            file_extension=file_extension,
            model_specific_instructions=model_instructions,
        )

    def _get_instruction_key(self) -> str:
        """Get the model key for prompt instructions."""
        return (
            self.__class__.__name__.lower().replace("model", "").replace("provider", "")
        )

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Generate text from the model.

        Args:
            prompt: The text prompt
            images: Optional list of base64-encoded images for multimodal models
            temperature: Sampling temperature (default from config)
            max_tokens: Maximum tokens to generate (default from config)

        Returns:
            Generated text response
        """
        self._ensure_model_loaded()

        temp = temperature if temperature is not None else self.config["temperature"]
        max_tok = max_tokens if max_tokens is not None else self.config["max_tokens"]

        try:
            if images:
                # Multimodal generation with images
                content_parts: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
                for img_b64 in images:
                    content_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                        }
                    )

                messages = [
                    {
                        "role": "system",
                        "content": "You are a document analysis expert.",
                    },
                    {"role": "user", "content": content_parts},
                ]

                response = self.model.create_chat_completion(
                    messages=messages, temperature=temp, max_tokens=max_tok
                )
            else:
                # Text-only generation
                response = self.model.create_completion(
                    prompt=prompt,
                    temperature=temp,
                    max_tokens=max_tok,
                    stop=["<|im_end|>", "<|endoftext|>"],
                )

            # Extract response text
            if isinstance(response, dict):
                if "choices" in response and response["choices"]:
                    choice = response["choices"][0]
                    if "message" in choice:
                        return choice["message"].get("content", "")
                    elif "text" in choice:
                        return choice["text"]
                elif "content" in response:
                    return response["content"]

            logger.warning(
                "unexpected_response_format", response_type=str(type(response))
            )
            return str(response)

        except Exception as e:
            logger.error("llama_cpp_generation_failed", error=str(e))
            raise RuntimeError(f"Model generation failed: {e}")

    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract information from text and/or image.

        This is the main interface method expected by DocumentProcessor.

        Args:
            text: Extracted text content from document
            image_path: Optional path to image for vision models

        Returns:
            Dictionary with extraction results including 'raw_analysis', 'success', etc.
        """
        try:
            # Generate enhanced prompt
            prompt = self._generate_enhanced_prompt(text)

            # Handle image if provided
            images = None
            if image_path:
                try:
                    images = [self._encode_image(image_path)]
                    logger.debug("image_encoded", image_path=image_path)
                except Exception as e:
                    logger.warning(
                        "image_encoding_failed", image_path=image_path, error=str(e)
                    )

            # Generate response
            response_text = self.generate(prompt, images=images)

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
                "model_name": Path(self.model_path).name,
                "success": True,
                "validation_passed": is_valid,
                "validation_errors": errors if errors else None,
                "provider": "llama.cpp",
            }

            if not is_valid:
                logger.warning("llama_cpp_validation_failed", validation_errors=errors)

            return result

        except Exception as e:
            logger.error("llama_cpp_extraction_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "model_name": Path(self.model_path).name
                if self.model_path
                else "unknown",
                "provider": "llama.cpp",
            }

    async def extract_information_async(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Async wrapper for extract_information using run_in_executor.

        Args:
            text: Extracted text content from document
            image_path: Optional path to image for vision analysis

        Returns:
            Dictionary with extraction results (same structure as sync version)
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.extract_information, text, image_path
        )

    @classmethod
    def is_available(cls) -> bool:
        """
        Check if the model is available.

        For llama.cpp models, this checks if the GGUF file exists.
        Subclasses should override _get_model_path() and this will check it.

        Returns:
            True if model can be loaded, False otherwise
        """
        try:
            # Get model path from subclass
            model_path = cls._get_model_path()

            if not model_path:
                logger.debug("llama_cpp_no_model_path", class_name=cls.__name__)
                return False

            exists = Path(model_path).exists()
            if exists:
                logger.info(
                    "llama_cpp_model_found",
                    class_name=cls.__name__,
                    model_path=model_path,
                )
            else:
                logger.debug(
                    "llama_cpp_model_not_found",
                    class_name=cls.__name__,
                    model_path=model_path,
                )

            return exists

        except NotImplementedError:
            # Base class doesn't implement _get_model_path
            return False
        except Exception as e:
            logger.error(
                "llama_cpp_availability_check_failed",
                class_name=cls.__name__,
                error=str(e),
            )
            return False

    def get_capabilities(self) -> Dict[str, bool]:
        """
        Get model capabilities.

        Returns:
            Dictionary of capability flags
        """
        return {
            "vision": True,  # Most GGUF models support vision
            "multilingual": True,
            "streaming": False,  # llama.cpp streaming can be added later
            "structured_output": True,
            "local": True,
            "gpu_acceleration": self.config["n_gpu_layers"] > 0,
        }
