"""
DocFlow Model Providers Package

Provides unified provider architecture for different LLM backends:
- llama.cpp for local GGUF models
- HTTP-based providers for API models
"""

from .base import BaseProvider, HTTPProvider, LocalProvider, ProviderCapabilities
from .llama_cpp_provider import LlamaCppProvider

__all__ = [
    "BaseProvider",
    "HTTPProvider",
    "LocalProvider",
    "ProviderCapabilities",
    "LlamaCppProvider",
]
