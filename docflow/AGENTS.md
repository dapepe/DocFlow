# DOCFLOW CORE KNOWLEDGE BASE

## OVERVIEW
The `docflow/` directory contains the core application logic, orchestrating document extraction, AI model interaction, and multi-interface access (CLI/API).

## STRUCTURE
```
docflow/
├── cli.py              # Base Click CLI definitions
├── enhanced_cli.py     # Advanced workflows & batch processing
├── processor.py        # Main document processing pipeline
├── config.py           # Settings & environment management
├── utils.py            # Stateless helper functions
├── api.py              # FastAPI route definitions
└── models/             # Provider-specific implementations
```

## WHERE TO LOOK
| Component | File | Responsibility |
|-----------|------|----------------|
| **CLI (Base)** | `cli.py` | Standard entry points and help text. |
| **CLI (Advanced)** | `enhanced_cli.py` | Complex workflows and interactive modes. |
| **Pipeline** | `processor.py` | Orchestration of extraction -> model -> output. |
| **Config** | `config.py` | Loading `rules.yaml` and `.env` variables. |
| **Helpers** | `utils.py` | File I/O, path normalization, and logging setup. |

## CONVENTIONS
*   **CLI Split**: Use `cli.py` for atomic commands; `enhanced_cli.py` for multi-step workflows.
*   **Pipeline First**: All document logic must reside in `processor.py` to ensure API/CLI parity.
*   **Config vs Utils**: `config.py` is for application state/settings; `utils.py` is for pure, stateless functions.

## ANTI-PATTERNS
*   **Core Conflict**: NEVER use `core.py`. It is a legacy duplicate of `processor.py` and should be ignored or removed.
*   **Logic Leakage**: Do not implement processing logic directly in `api.py` or `cli.py`; always delegate to `processor.py`.
*   **Hardcoded Paths**: Avoid hardcoding paths in `utils.py`; use `config.py` managed settings.
