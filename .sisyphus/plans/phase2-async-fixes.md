# Phase 2: Async Architecture - Critical Fixes

## TL;DR

> **Quick Summary**: Fix blocking bugs introduced during async migration. Tests are broken due to syntax error in llama_cpp_provider.py and missing import in ollama_base.py.
> 
> **Deliverables**:
> - All 65 tests passing again
> - Clean async architecture with no circular imports
> - Beads updated to reflect completion
> 
> **Estimated Effort**: Short (1-2 hours)
> **Parallel Execution**: NO - sequential fixes required
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5

---

## Context

### Original Request
Phase 2 async migration introduced native async support (httpx, aiofiles, extract_information_async) across the provider architecture. The implementation is ~90% complete but has 3 blocking bugs that break all tests.

### Current State
- **Tests**: ALL FAILING (SyntaxError at import time)
- **Root Cause 1**: `docflow/models/providers/llama_cpp_provider.py` has corrupted docstring (duplicate text outside quotes on lines 28-37)
- **Root Cause 2**: `docflow/models/ollama_base.py` uses `@cached_model_response_async` decorator but does NOT import it
- **Root Cause 3**: `docflow/models/providers/llama_cpp_provider.py` missing `**kwargs` in `generate()` signature and missing `extract_information_async` method

### What Was Already Done (Do NOT Redo)
- `docflow/models/providers/base.py`: HTTPProvider has `_make_request_async`, `_get_async_client`, `__aenter__`, `__aexit__`. BaseProvider has abstract `extract_information_async`.
- `docflow/models/__init__.py`: BaseModel inherits BaseProvider, has default `extract_information_async` wrapper.
- `docflow/models/openrouter_base.py`: Has `extract_information_async` with `@cached_model_response_async`.
- `docflow/models/ollama_base.py`: Has `extract_information_async` with `@cached_model_response_async` decorator (but MISSING the import).
- `docflow/processor.py`: Has `_extract_text_async` helpers, `self.executor = ThreadPoolExecutor(max_workers=4)`, refactored `process_document_async`.
- `docflow/api.py`: `/process` endpoint uses `await processor.process_document_async()`.
- `docflow/performance_optimizer.py`: Has `cached_model_response_async` function.

---

## Work Objectives

### Core Objective
Fix the 3 blocking bugs so all 65 tests pass again.

### Must Have
- SyntaxError in llama_cpp_provider.py fixed
- Missing import in ollama_base.py fixed
- generate() signature compatible with BaseProvider
- extract_information_async implemented in LlamaCppProvider
- All 65 tests green

### Must NOT Have (Guardrails)
- Do NOT refactor anything beyond the specific fixes
- Do NOT change test files
- Do NOT modify BaseProvider, HTTPProvider, or processor.py (they are correct)

---

## TODOs

- [ ] 1. Fix corrupted docstring in llama_cpp_provider.py

  **What to do**:
  - Open `docflow/models/providers/llama_cpp_provider.py`
  - Lines 21-37 currently have:
    ```python
    class LlamaCppProvider(LocalProvider):
        """
        Base provider for llama.cpp GGUF models.
        
        Loads models directly via llama-cpp-python for optimal performance.
        Supports both text-only and multimodal (vision) models.
        """
        Base provider for llama.cpp GGUF models.     # <-- REMOVE
        
        Loads models directly via llama-cpp-python... # <-- REMOVE
        Supports both text-only and multimodal...     # <-- REMOVE
        """                                           # <-- REMOVE
        Base provider for llama.cpp GGUF models.     # <-- REMOVE
        ...                                          # <-- REMOVE
        """                                          # <-- REMOVE
    ```
  - Replace lines 21-37 with:
    ```python
    class LlamaCppProvider(LocalProvider):
        """Base provider for llama.cpp GGUF models."""
    ```
  - Lines 28-37 (the duplicated text) must be completely removed

  **Must NOT do**:
  - Do not change any other part of the file in this task

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Tasks 2, 3, 4, 5

  **References**:
  - `docflow/models/providers/llama_cpp_provider.py:21-39` - The corrupted section

  **Acceptance Criteria**:
  - [ ] Lines 28-37 (duplicate docstring text) removed
  - [ ] Class definition is syntactically valid Python
  - [ ] `python -c "from docflow.models.providers.llama_cpp_provider import LlamaCppProvider"` does NOT raise SyntaxError

  **Commit**: NO (group with Task 2)

---

- [ ] 2. Fix missing import in ollama_base.py

  **What to do**:
  - Open `docflow/models/ollama_base.py`
  - Line 16 currently reads:
    ```python
    from ..performance_optimizer import cached_model_response, optimize_text_extraction
    ```
  - Change to:
    ```python
    from ..performance_optimizer import cached_model_response, cached_model_response_async, optimize_text_extraction
    ```

  **Must NOT do**:
  - Do not change any other imports or code

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Task 1
  - **Blocks**: Tasks 3, 4, 5

  **References**:
  - `docflow/models/ollama_base.py:16` - The import line
  - `docflow/models/ollama_base.py:210` - Where `@cached_model_response_async` is used

  **Acceptance Criteria**:
  - [ ] `cached_model_response_async` is imported on line 16
  - [ ] `python -c "from docflow.models.ollama_base import OllamaBaseModel"` does NOT raise NameError

  **Commit**: NO (group with Task 3)

---

- [ ] 3. Fix generate() signature and add extract_information_async to LlamaCppProvider

  **What to do**:
  - Open `docflow/models/providers/llama_cpp_provider.py`
  - Find `def generate(self, prompt, images=None, temperature=None, max_tokens=None) -> str:` (around line 176)
  - Add `**kwargs` parameter to match BaseProvider signature:
    ```python
    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
    ```
  - Add `extract_information_async` method BEFORE `is_available` (around line 335):
    ```python
    async def extract_information_async(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.extract_information, text, image_path)
    ```

  **Must NOT do**:
  - Do not modify extract_information (sync version)
  - Do not change _load_model or any other methods

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Tasks 1, 2
  - **Blocks**: Tasks 4, 5

  **References**:
  - `docflow/models/providers/base.py:64-71` - BaseProvider.generate signature (must match)
  - `docflow/models/providers/base.py:111-125` - BaseProvider.extract_information_async (abstract)
  - `docflow/models/ollama_base.py:210-265` - OllamaBaseModel.extract_information_async (pattern to follow)

  **Acceptance Criteria**:
  - [ ] `generate()` has `**kwargs` parameter
  - [ ] `extract_information_async` method exists
  - [ ] `python -c "from docflow.models.providers.llama_cpp_provider import LlamaCppProvider"` succeeds

  **Commit**: YES
  - Message: `fix: resolve async migration blocking bugs (corrupted docstring, missing import, method signatures)`
  - Files: `docflow/models/providers/llama_cpp_provider.py`, `docflow/models/ollama_base.py`
  - Pre-commit: `./.venv/bin/python3 -c "from docflow.models import ModelRegistry"`

---

- [ ] 4. Run full test suite and fix any remaining failures

  **What to do**:
  - Run `./.venv/bin/python3 -m pytest tests/`
  - If any tests fail, fix them
  - Expected: 65 tests should pass (same as before async migration)
  - Known potential issue: `test_model_registry.py::test_registry_lists_new_ollama_models` may still fail due to mocking. If so, ensure `requests.get` mock uses `*args, **kwargs` signature (not `self, url, timeout=None`)

  **Must NOT do**:
  - Do not skip or delete tests
  - Do not mark tests as xfail

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Task 3

  **References**:
  - `tests/test_model_registry.py:37` - The mock function `_fake_get(*args, **kwargs)`
  - `tests/conftest.py` - Shared fixtures

  **Acceptance Criteria**:
  - [ ] `./.venv/bin/python3 -m pytest tests/` → 65 passed, 0 failed

  **Commit**: YES (if fixes needed)
  - Message: `test: fix test regressions from async migration`
  - Pre-commit: `./.venv/bin/python3 -m pytest tests/`

---

- [ ] 5. Update beads and sync

  **What to do**:
  - Close remaining Phase 2 beads:
    ```bash
    bd close DocFlow-oix.1.1  # Already closed
    bd close DocFlow-oix.1.2  # Already closed
    bd close DocFlow-oix.1.3  # Already closed
    bd sync
    ```
  - Verify with `bd list`

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Task 4

  **Acceptance Criteria**:
  - [ ] All Phase 2.1 beads closed
  - [ ] `bd sync` succeeds
  - [ ] Final git commit includes beads state

  **Commit**: YES
  - Message: `chore: sync beads state for Phase 2.1 completion`

---

## Success Criteria

### Verification Commands
```bash
./.venv/bin/python3 -c "from docflow.models import ModelRegistry; print('Import OK')"
./.venv/bin/python3 -m pytest tests/  # Expected: 65 passed
bd list --status=open  # Expected: Phase 2.2+ tasks only
```

### Final Checklist
- [ ] No SyntaxError on import
- [ ] No NameError on import
- [ ] All 65 tests pass
- [ ] Beads reflect accurate state
