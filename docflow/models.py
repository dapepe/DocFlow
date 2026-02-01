"""
Legacy models file for backward compatibility.
All new model implementations should be added to the models/ directory.
"""
from .models import BaseModel as BaseAIModel
from .models import ModelRegistry

__all__ = ['BaseAIModel', 'ModelRegistry']