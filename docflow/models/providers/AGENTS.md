# MODEL PROVIDERS KNOWLEDGE BASE

## OVERVIEW
This directory contains the abstract interface definitions and base implementations for AI model providers. It decouples the core document processing logic from specific model backends (Ollama, llama.cpp, OpenAI, etc.).

## CORE ABSTRACTIONS
*   **BaseProvider (ABC)**: The root interface for all providers. Defines mandatory methods like `generate()`, `extract_information()`, and `is_available()`.
*   **HTTPProvider**: Specialized base for API-based models. Handles session management, connection pooling, and retry logic (e.g., for OpenRouter, OpenAI).
*   **LocalProvider**: Specialized base for models running on local hardware. Manages model loading/unloading, memory, and GPU acceleration (e.g., for llama.cpp, vLLM).
*   **ProviderCapabilities**: A standard set of flags (vision, ocr, local, etc.) used to match models to specific document processing requirements.

## WHERE TO LOOK
| Component | File | Responsibility |
|-----------|------|----------------|
| **Base Classes** | `base.py` | `BaseProvider`, `HTTPProvider`, `LocalProvider` |
| **Capabilities** | `base.py` | `ProviderCapabilities` definition |
| **GGUF Support** | `llama_cpp_provider.py` | Direct local inference via llama-cpp-python |

## CONVENTIONS
*   **Lazy Loading**: Local models should be loaded only when first needed via `_ensure_model_loaded()`.
*   **Capability Reporting**: Always populate `self.capabilities` in `__init__` to allow the registry to filter models.
*   **Error Handling**: `HTTPProvider` implementations should leverage the built-in retry logic for transient network errors.
*   **Resource Management**: `LocalProvider` must implement `unload_model()` to free VRAM/RAM when the provider is destroyed.
