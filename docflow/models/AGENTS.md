# AI MODELS KNOWLEDGE BASE

## OVERVIEW
Plugin-based AI model system. Models self-register via `ModelRegistry` in `__init__.py`.
Supports local (Ollama), cloud (OpenRouter), and direct API integration.

## STRUCTURE
```
models/
├── __init__.py          # Registry, BaseModel & Dynamic Loader
├── providers/           # Abstract provider interfaces (BaseProvider)
├── ollama_base.py       # Base for local Ollama models
├── openrouter_base.py   # Base for OpenRouter models
└── {model_name}.py      # Specific model implementations
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Registry Logic** | `__init__.py` | `ModelRegistry` class, `load_models()` |
| **Base Interface** | `__init__.py` | `BaseModel` abstract class |
| **Provider Split** | `providers/` | `BaseProvider`, `HTTPProvider`, `LocalProvider` |
| **Local Models** | `ollama_base.py` | Shared logic for Ollama-based models |
| **Cloud Models** | `openrouter_base.py` | Shared logic for OpenRouter-based models |

## CONVENTIONS
*   **Inheritance**: Inherit from `OllamaBaseModel`, `OpenRouterBaseModel`, or `BaseModel`.
*   **Registration**: Models MUST call `ModelRegistry.register(id, Class)` at module level.
*   **Availability**: Implement `is_available()` to check for service/env var presence.
*   **Provider Split**: Use `providers/` for generic backend logic; `models/` for specific model behavior.

## ANTI-PATTERNS
*   **Direct Instantiation**: NEVER instantiate models directly; use `ModelRegistry.get_model()`.
*   **Hardcoded Fallbacks**: Avoid hardcoding "fallback" logic; let the registry handle availability.
*   **Logic Duplication**: Do not reimplement HTTP/Ollama logic; use the base classes.
