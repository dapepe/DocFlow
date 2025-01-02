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
        return cls._models.get(model_id)

    @classmethod
    def list_models(cls) -> Dict[str, str]:
        """List all registered models and their descriptions"""
        return {
            model_id: model_class.description
            for model_id, model_class in cls._models.items()
            if hasattr(model_class, 'is_available') and model_class.is_available()
        }

class BaseModel(ABC):
    """Base class for all AI models"""
    description: str = "Base AI Model"
    requires_env_vars: list = []

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if the model is available in the current environment"""
        return True

    @abstractmethod
    def extract_information(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract information from text and/or image"""
        pass

# For backward compatibility
BaseAIModel = BaseModel

# Import all model implementations
def load_models():
    """Dynamically load all model implementations"""
    models_dir = Path(__file__).parent
    for model_file in models_dir.glob("*.py"):
        if model_file.stem not in ["__init__", "base"]:
            module_name = f"{__package__}.{model_file.stem}"
            try:
                importlib.import_module(module_name)
                logger.debug(f"Loaded model module: {module_name}")
            except Exception as e:
                logger.error(f"Error loading model {module_name}: {e}")

# Load models on package initialization
load_models()

# Export base classes and registry
__all__ = ['BaseModel', 'BaseAIModel', 'ModelRegistry']