"""
DocFlow Models Package
Provides dynamic model loading and registration functionality.
"""
from typing import Dict, Type, Optional
from pathlib import Path
import importlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class ModelRegistry:
    """Central registry for AI models"""
    _models: Dict[str, Type['BaseModel']] = {}

    @classmethod
    def register(cls, model_id: str, model_class: Type['BaseModel']) -> None:
        """Register a model class with the registry"""
        cls._models[model_id] = model_class
        logger.info(f"Registered model: {model_id}")

    @classmethod
    def get_model(cls, model_id: str) -> Optional[Type['BaseModel']]:
        """Get a model class by its ID"""
        model = cls._models.get(model_id)
        if model:
            logger.info(f"Retrieved model {model_id} from registry")
        else:
            logger.warning(f"Model {model_id} not found in registry")
        return model

    @classmethod
    def list_models(cls) -> Dict[str, str]:
        """List all registered models and their descriptions"""
        models = {}
        logger.info(f"Checking availability for {len(cls._models)} registered models")

        # Always include fallback model first
        fallback_model = cls._models.get('fallback')
        if fallback_model:
            models['fallback'] = fallback_model.description
            logger.info("Added fallback model to available models")

        # Check other models
        for model_id, model_class in cls._models.items():
            if model_id != 'fallback':  # Skip fallback as it's already added
                try:
                    # Log environment variables for debugging
                    if hasattr(model_class, 'requires_env_vars'):
                        env_vars = {var: bool(os.getenv(var)) for var in getattr(model_class, 'requires_env_vars', [])}
                        logger.info(f"Model {model_id} environment variables: {env_vars}")

                    # Check availability
                    is_available = model_class.is_available()
                    logger.info(f"Model {model_id} availability check: {is_available}")

                    if is_available:
                        models[model_id] = getattr(model_class, 'description', 'No description available')
                        logger.info(f"Model {model_id} is available")
                except Exception as e:
                    logger.error(f"Error checking availability for model {model_id}: {e}", exc_info=True)

        return models

class BaseModel(ABC):
    """Base class for all AI models"""
    description: str = "Base AI Model"
    requires_env_vars: list = []

    @classmethod
    def is_available(cls) -> bool:
        """Check if the model is available in the current environment"""
        # Fallback model is always available
        if cls.__name__ == 'FallbackModel':
            return True

        # For other models, check implementation-specific availability
        try:
            return True
        except Exception as e:
            logger.error(f"Error checking availability for {cls.__name__}: {e}")
            return False

    @abstractmethod
    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information from text and/or image"""
        pass

# For backward compatibility
BaseAIModel = BaseModel

def load_models():
    """Dynamically load all model implementations"""
    models_dir = Path(__file__).parent
    logger.info(f"Loading models from directory: {models_dir}")
    for model_file in models_dir.glob("*.py"):
        if model_file.stem not in ["__init__", "base"]:
            module_name = f"{__package__}.{model_file.stem}"
            try:
                importlib.import_module(module_name)
                logger.info(f"Successfully loaded model module: {module_name}")
            except Exception as e:
                logger.error(f"Error loading model {module_name}: {e}", exc_info=True)

# Load models on package initialization
load_models()

# Export base classes and registry
__all__ = ['BaseModel', 'BaseAIModel', 'ModelRegistry']