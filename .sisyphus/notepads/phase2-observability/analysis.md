# Phase 2: Observability - Codebase Analysis

**Date**: 2026-02-14  
**Status**: PREPARATION (not yet in active plan)  
**Scope**: Structured logging & request ID tracing implementation

## CURRENT STATE SUMMARY

### Logging Architecture
- **Pattern**: Standard `logging.getLogger(__name__)` across 26 files
- **Format**: Unstructured string interpolation (f-strings)
- **Request Correlation**: NONE - no way to trace a single request through system
- **Context Variables**: NOT USED - no contextvars for async context propagation

### Request Handling
- **Middleware**: CORS only (no request ID middleware)
- **Request ID**: NOT GENERATED or tracked
- **Context Propagation**: MISSING - API → processor → models have no shared context
- **Async Support**: Partial (async methods exist but no context management)

### Dependencies
- **structlog**: NOT in requirements.txt (needed for structured logging)
- **contextvars**: Built-in (no dependency needed)
- **Available**: aiofiles, httpx, pydantic-settings (already in use)

## KEY FINDINGS

### 1. Logging Usage (26 files, 150+ log calls)
```
Core:
  - api.py: 11 calls (errors, warnings)
  - processor.py: 40+ calls (info, debug, error)
  - models/__init__.py: 10 calls (registry operations)

Models (13 files):
  - ollama_base.py: 8 calls
  - openrouter_base.py: 8 calls
  - qwen_vision.py, llava.py, granite_vision.py, gemma.py, llama_vision.py: 3 each
  - fallback.py: 2 calls
  - llama32_vision.py, olmocr_model.py, qwen25_vl.py: 1 each
  - providers/base.py: 5 calls
  - providers/llama_cpp_provider.py: 10+ calls

Utilities:
  - layout_processor.py: 7 calls
  - model_router.py: 7 calls
  - performance_optimizer.py: 5 calls
  - prompt_manager.py: 5 calls
  - response_validator.py: 3 calls
  - cli/main.py: 5 calls
```

### 2. Request Flow (No Context)
```
POST /process
  ↓
DocumentProcessor.__init__(ai_model)
  ├─ No request_id parameter
  ├─ No context variable access
  └─ process_document_async()
      ├─ _extract_text_from_pdf()
      ├─ _classify_document()
      └─ _analyze_with_ai()
          └─ ai_model.extract_information_async()
              └─ Logs have NO request_id
```

### 3. Missing Components
- [ ] Request ID generation (UUID)
- [ ] Request ID middleware (FastAPI)
- [ ] Context variable (contextvars.ContextVar)
- [ ] Structured logging (structlog)
- [ ] Context propagation (processor, models)
- [ ] Async context management

## IMPLEMENTATION ROADMAP

### Phase 2.2: Structured Logging Setup (2-3 hours)
1. Add `structlog>=24.1.0` to requirements.txt
2. Create `docflow/middleware/request_id.py` (RequestIDMiddleware)
3. Create `docflow/logging_config.py` (structlog configuration)
4. Update `docflow/api.py` (register middleware)
5. Update `main.py` (initialize logging)

### Phase 2.3: Processor Integration (1-2 hours)
1. Update `DocumentProcessor.__init__()` to accept/extract request_id
2. Convert all logger calls to structlog
3. Add request_id to all log calls

### Phase 2.4: Model Integration (3-4 hours)
1. Update all 13 model classes to use structlog
2. Add request_id to all log calls
3. Update BaseModel for context support

### Phase 2.5: Testing & Validation (1-2 hours)
1. Test RequestIDMiddleware
2. Test request ID propagation
3. Test structured log format
4. Verify all 65 tests pass

## EFFORT ESTIMATE
- **Total**: 7-11 hours
- **Complexity**: Medium (many files, but repetitive pattern)
- **Risk**: Low (isolated changes, backward compatible)
- **Parallelization**: NO (sequential dependencies)

## NEXT STEPS
1. Confirm Phase 2.2 approval in roadmap
2. Create beads with 5 sub-tasks
3. Execute sequentially
4. Validate with full test suite
