"""
DocFlow Models Package
Provides dynamic model loading and registration functionality.
"""

from typing import Dict, Type, Optional
from pathlib import Path
import importlib
import structlog
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
import asyncio
from .providers.base import BaseProvider

logger = structlog.get_logger(__name__)


class ModelRegistry:
    """Central registry for AI models"""

    _models: Dict[str, Type["BaseProvider"]] = {}

    @classmethod
    def register(cls, model_id: str, model_class: Type["BaseProvider"]) -> None:
        """Register a model class with the registry"""
        cls._models[model_id] = model_class
        logger.info(
            "model_registered", model_id=model_id, model_class=model_class.__name__
        )

    @classmethod
    def get_model(cls, model_id: str) -> Optional[Type["BaseProvider"]]:
        """Get a model class by its ID"""
        model = cls._models.get(model_id)
        if model:
            logger.info(
                "model_retrieved", model_id=model_id, model_class=model.__name__
            )
        else:
            logger.warning("model_not_found", model_id=model_id)
        return model

    @classmethod
    def list_models(cls) -> Dict[str, str]:
        """List all registered models and their descriptions"""
        models = {}
        logger.info("checking_model_availability", total_models=len(cls._models))

        # Always include fallback model first
        fallback_model = cls._models.get("fallback")
        if fallback_model:
            models["fallback"] = fallback_model.description
            logger.info("fallback_model_added")

        # Check other models
        for model_id, model_class in cls._models.items():
            if model_id != "fallback":  # Skip fallback as it's already added
                try:
                    # Log environment variables for debugging
                    if hasattr(model_class, "requires_env_vars"):
                        env_vars = {
                            var: bool(os.getenv(var))
                            for var in getattr(model_class, "requires_env_vars", [])
                        }
                        logger.info(
                            "model_env_vars_checked",
                            model_id=model_id,
                            env_vars=env_vars,
                        )

                    # Check availability
                    is_available = model_class.is_available()
                    logger.info(
                        "model_availability_checked",
                        model_id=model_id,
                        is_available=is_available,
                    )

                    if is_available:
                        models[model_id] = getattr(
                            model_class, "description", "No description available"
                        )
                        logger.info("model_available", model_id=model_id)
                except Exception as e:
                    logger.error(
                        "model_availability_check_failed",
                        model_id=model_id,
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True,
                    )

        return models


class BaseModel(BaseProvider):
    """Base class for all AI models (Backward Compatibility Wrapper)"""

    # Default implementations
    def _load_config(self) -> Dict[str, Any]:
        return {}

    def generate(self, prompt: str, **kwargs) -> str:
        return ""

    @classmethod
    def is_available(cls) -> bool:
        """Check if the model is available in the current environment"""
        # Fallback model is always available
        if cls.__name__ == "FallbackModel":
            return True

        # For other models, check implementation-specific availability
        try:
            return True
        except Exception as e:
            logger.error(
                "availability_check_failed",
                model_class=cls.__name__,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    @abstractmethod
    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract information from text and/or image"""
        pass

    async def extract_information_async(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Default async implementation wrapping sync method"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.extract_information, text, image_path
        )


# For backward compatibility
BaseAIModel = BaseModel


def load_models():
    """Dynamically load all model implementations"""
    models_dir = Path(__file__).parent
    logger.info("loading_models", models_dir=str(models_dir))
    for model_file in models_dir.glob("*.py"):
        if model_file.stem not in ["__init__", "base"]:
            module_name = f"{__package__}.{model_file.stem}"
            try:
                importlib.import_module(module_name)
                logger.info("model_module_loaded", module_name=module_name)
            except Exception as e:
                logger.error(
                    "model_module_load_failed",
                    module_name=module_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )


# Load models on package initialization
load_models()

# Export base classes and registry
__all__ = ["BaseModel", "BaseAIModel", "ModelRegistry"]
