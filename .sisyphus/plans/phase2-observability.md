# Phase 2: Reliability Hardening - Observability (Structured Logging & Tracing)

## TL;DR

> **Quick Summary**: Implement structured logging (via `structlog`) and request ID tracing across the entire async pipeline to enable correlation of logs per request.
> 
> **Deliverables**:
> - `structlog` integration replacing standard logging
> - `RequestIDMiddleware` for FastAPI
> - `x-request-id` propagation in logs and headers
> - All 65 tests passing
> 
> **Estimated Effort**: Medium (5-6 hours)
> **Parallel Execution**: NO - sequential implementation required
> **Critical Path**: Setup → API → Processor → Models → Verification

---

## Context

### Current State
- **Logging**: Standard Python `logging` with unstructured f-strings.
- **Tracing**: No request ID correlation. Logs from concurrent requests are interleaved and indistinguishable.
- **Context**: No context propagation (request ID lost after API layer).

### Goal
Enable full observability by ensuring every log line contains a unique `request_id` and structured metadata, allowing for precise debugging of async flows.

---

## Work Objectives

### Core Objective
Replace unstructured logging with `structlog` and implement request tracing.

### Must Have
- `structlog` configured for JSON output (prod) and console (dev)
- `RequestIDMiddleware` generating UUIDs
- `request_id` context variable propagated through `contextvars`
- All loggers updated to use `structlog.get_logger()`
- Backward compatibility for existing `logging` calls (where possible)

### Must NOT Have
- Do NOT break existing tests
- Do NOT introduce performance regressions >5%

---

## TODOs

- [ ] 1. Setup & Configuration
  **What to do**:
  - Add `structlog>=24.1.0` to `requirements.txt`
  - Create `docflow/logging_config.py` with structlog configuration (JSON renderer, timestamp, log level)
  - Create `docflow/middleware/request_id.py` with `RequestIDMiddleware` using `contextvars`
  - Create `docflow/middleware/__init__.py`

  **Verification**:
  - `python -c "import structlog; print(structlog.get_logger().info('test'))"` outputs structured log
  - Middleware generates UUIDs

- [ ] 2. API Integration
  **What to do**:
  - Update `docflow/api.py`:
    - Configure logging on startup using `logging_config.configure()`
    - Add `RequestIDMiddleware` to FastAPI app
    - Update API endpoints to log request receipt/completion with structured logger

  **Verification**:
  - `curl -v http://localhost:8000/models` returns `x-request-id` header

- [ ] 3. Processor Integration
  **What to do**:
  - Update `docflow/processor.py`:
    - Replace `logging.getLogger` with `structlog.get_logger`
    - Update `process_document` and `process_document_async` to bind `request_id` context
    - Convert f-string logs to structured key-value pairs

  **Verification**:
  - Processing a document produces logs with `request_id` field

- [ ] 4. Model Integration (Batch 1: Base Classes)
  **What to do**:
  - Update `docflow/models/providers/base.py`
  - Update `docflow/models/providers/http_provider.py`
  - Update `docflow/models/providers/local_provider.py`
  - Update `docflow/models/__init__.py` (Registry)
  - Replace logging with structlog

- [ ] 5. Model Integration (Batch 2: Implementations)
  **What to do**:
  - Update all model implementations in `docflow/models/`:
    - `ollama_base.py`, `openrouter_base.py`
    - `qwen_vision.py`, `granite_vision.py`, `llama_vision.py`
    - `gemma.py`, `llava.py`, `mistral_document.py`
    - `gpt4_vision.py`, `fallback.py`
  - Ensure `extract_information` logs include model metadata

- [ ] 6. Final Verification & Beads
  **What to do**:
  - Run full test suite: `./.venv/bin/python3 -m pytest tests/`
  - Verify logs contain `request_id` during a real run
  - Update beads (DocFlow-oix.2 series)
  - Sync state

---

## Success Criteria

### Verification Commands
```bash
# Check headers
curl -I http://localhost:8000/models | grep -i x-request-id

# Check log format (should be JSON or structured key-value)
./.venv/bin/python3 main.py models

# Run tests
./.venv/bin/python3 -m pytest tests/
```

### Final Checklist
- [ ] `x-request-id` header present in responses
- [ ] Logs are structured (not just strings)
- [ ] Logs contain `request_id`
- [ ] All 65 tests pass
