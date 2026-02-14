# Milestone 1: Foundation & Cleanup

**Priority:** Critical
**Status:** Completed
**Theme:** "Less is More" - Removing debt to move faster.

## 1.1 Architecture Simplification
The project currently has "split brain" issues with multiple processors and CLI entry points.

- [x] **Remove Duplicate Core**: Delete `docflow/core.py` (legacy). Ensure `docflow/processor.py` is the single source of truth.
- [x] **Consolidate CLI**: Merge `cli.py`, `enhanced_cli.py`, `cli_workflows.py`, and `cli_help.py` into a clean `docflow/cli/` package or unified module.
- [x] **Fix Initialization**: Move `setup_logging()` out of `__init__.py` to prevent import side effects.

## 1.2 Model Layer Consolidation
Currently 26 model implementations across 5 backends. We will consolidate to the 3 most robust paths:
1.  **OpenRouter**: For ALL cloud models (GPT-4, Claude, Gemini).
2.  **Ollama**: For ALL local models (Llama 3, Qwen, Mistral).
3.  **Fallback**: For regex/rule-based processing.

**Actions:**
- [x] **Delete Legacy**: Remove `docflow/models-old.py`.
- [x] **Refactor Hierarchy**: Implement `HTTPProvider` (OpenRouter) and `LocalProvider` (Ollama) inheriting from `BaseProvider`.
- [x] **Deprecate/Remove**: Direct API implementations (maintenance burden) and raw `llama.cpp` (redundant with Ollama).
- [x] **Unify Image Handling**: Move image encoding/processing to the BaseProvider.

## 1.3 Code Hygiene
Fixing the "broken windows" in the codebase.

- [x] **Logging**: Replace all `print()` statements in `api.py` and models with `logger`.
- [x] **Error Handling**: Replace bare `except:` clauses with specific exceptions (`Exception` at minimum).
- [ ] **Type Safety**: Add type hints to all public methods in `processor.py` and `models/`. (Partial)
- [ ] **Exports**: Add `__all__` to modules to define public API.

## 1.4 Configuration & Testing
- [x] **Centralized Config**: Replace scattered `os.getenv` calls with a Pydantic `Settings` object.
- [x] **Fix Tests**: Repair the 8 broken tests in `tests/`.
- [x] **Test Structure**: Add `tests/conftest.py` for shared fixtures.
