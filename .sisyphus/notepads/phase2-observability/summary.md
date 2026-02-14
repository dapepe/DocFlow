# Phase 2: Observability - Executive Summary

**Prepared**: 2026-02-14  
**Status**: PREPARATION (awaiting approval)  
**Scope**: Structured Logging & Request ID Tracing

---

## QUICK FACTS

| Aspect | Finding |
|--------|---------|
| **Current Logging** | Standard Python logging (26 files, 150+ calls) |
| **Request Tracking** | NONE - no way to correlate logs from single request |
| **Structured Logging** | NOT IMPLEMENTED - all logs are unstructured strings |
| **Context Propagation** | MISSING - API → processor → models have no shared context |
| **Dependencies** | structlog NOT in requirements.txt |
| **Effort Estimate** | 6-7 hours (sequential, no parallelization) |
| **Risk Level** | LOW (isolated changes, backward compatible) |
| **Complexity** | MEDIUM (many files, but repetitive pattern) |

---

## PROBLEM STATEMENT

### Current Situation
When a request comes in to `/process`:
1. FastAPI receives request (no ID assigned)
2. DocumentProcessor processes document (no context)
3. AI models analyze content (no request correlation)
4. Logs are generated (no way to trace single request)

**Result**: If something fails, you can't easily trace which logs belong to which request.

### Example
```
2026-02-14 16:35:42,123 - docflow.processor - INFO - Available AI models: [...]
2026-02-14 16:35:43,456 - docflow.models.qwen_vision - INFO - Initialized Qwen Vision model
2026-02-14 16:35:44,789 - docflow.processor - INFO - Successfully processed document: invoice.pdf
```

**Question**: Which request do these logs belong to? No way to tell!

---

## SOLUTION OVERVIEW

### 3-Part Implementation

#### Part 1: Request ID Middleware
- Generate UUID for each request
- Store in async context variable (contextvars)
- Add to response headers for client tracking

#### Part 2: Structured Logging
- Add `structlog` library
- Replace string interpolation with structured fields
- Automatically include request_id in all logs

#### Part 3: Context Propagation
- Pass request_id through processor
- Pass request_id through models
- Include in all log calls

### Expected Result
```json
{
  "timestamp": "2026-02-14T16:35:42.123Z",
  "level": "info",
  "logger": "docflow.processor",
  "message": "available_models_loaded",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "models": ["qwen-vision", "granite-vision"],
  "count": 2
}
```

**Benefit**: All logs for a request have the same `request_id` - easy to trace!

---

## IMPLEMENTATION ROADMAP

### Phase 2.2.1: Setup (1 hour)
- Add `structlog>=24.1.0` to requirements.txt
- Create `docflow/middleware/request_id.py` (RequestIDMiddleware)
- Create `docflow/logging_config.py` (structlog configuration)

### Phase 2.2.2: API Integration (30 min)
- Update `docflow/api.py` to register middleware
- Initialize logging on startup

### Phase 2.2.3: Processor Integration (1 hour)
- Update `DocumentProcessor` to accept/extract request_id
- Convert all logger calls to structlog
- Add request_id to all log calls

### Phase 2.2.4: Model Integration (2 hours)
- Update all 13 model classes to use structlog
- Add request_id to all log calls
- Update BaseModel for context support

### Phase 2.2.5: Testing & Validation (1 hour)
- Test RequestIDMiddleware
- Test request ID propagation
- Test structured log format
- Verify all 65 tests pass

---

## KEY DECISIONS

### 1. Use structlog (NOT python-json-logger)
**Why**: Native async support, structured fields, minimal overhead

### 2. Use contextvars (NOT thread-local)
**Why**: Async-safe, works across await boundaries, standard library

### 3. Implement Middleware (NOT decorator)
**Why**: Applies to ALL endpoints automatically, proper async handling

### 4. Keep Backward Compatibility
**Why**: Existing code still works, gradual migration possible

---

## FILES AFFECTED

### Create (3 files)
```
docflow/middleware/__init__.py
docflow/middleware/request_id.py
docflow/logging_config.py
```

### Modify (2 files)
```
requirements.txt
docflow/api.py
```

### Update (26 files)
```
docflow/processor.py
docflow/models/*.py (13 files)
docflow/layout_processor.py
docflow/model_router.py
docflow/performance_optimizer.py
docflow/prompt_manager.py
docflow/response_validator.py
docflow/cli/main.py
```

---

## EFFORT BREAKDOWN

| Phase | Task | Effort | Blocker |
|-------|------|--------|---------|
| 2.2.1 | Setup | 1 hour | None |
| 2.2.2 | API | 30 min | 2.2.1 |
| 2.2.3 | Processor | 1 hour | 2.2.2 |
| 2.2.4 | Models | 2 hours | 2.2.3 |
| 2.2.5 | Testing | 1 hour | 2.2.4 |
| **Total** | | **5.5 hours** | Sequential |

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|-----------|
| structlog version conflicts | Medium | Pin version in requirements.txt |
| Async context propagation issues | High | Use contextvars properly, test thoroughly |
| Performance overhead | Low | structlog is optimized for async |
| Breaking changes | Medium | Keep backward compatibility |
| Missing request_id in logs | High | Add to all log calls, test coverage |

---

## SUCCESS CRITERIA

### Verification Commands
```bash
# Check imports work
python -c "from docflow.middleware.request_id import RequestIDMiddleware"
python -c "from docflow.logging_config import configure_logging"

# Run tests
pytest tests/  # Expected: 65 passed

# Check logs have request_id
curl -X POST http://localhost:8000/process -F "file=@test.pdf" 2>&1 | grep request_id
```

### Final Checklist
- [ ] structlog installed and importable
- [ ] RequestIDMiddleware generates UUIDs
- [ ] Request ID in response headers
- [ ] Request ID in context variable
- [ ] Processor receives request_id
- [ ] All log calls include request_id
- [ ] Structured fields in logs
- [ ] All 65 tests pass
- [ ] No performance regression
- [ ] Logs are queryable by request_id

---

## NEXT STEPS

1. **Review this analysis** with team
2. **Approve Phase 2.2** in project roadmap
3. **Create beads** with 5 sub-tasks (one per phase)
4. **Assign to agent** with `git-master` skill
5. **Execute sequentially** (tasks are dependent)
6. **Validate** with full test suite

---

## APPENDIX: LOGGING PATTERNS

### Current Pattern (Unstructured)
```python
logger = logging.getLogger(__name__)
logger.info(f"Processing {filename} with {model}")
logger.error(f"Failed: {error}")
```

### New Pattern (Structured)
```python
logger = structlog.get_logger(__name__)
logger.info("document_processing_started", request_id=request_id, filename=filename, model=model)
logger.error("document_processing_failed", request_id=request_id, error=str(error), exc_info=True)
```

### Benefits
- **Queryable**: Filter logs by request_id, model, filename, etc.
- **Parseable**: JSON format for log aggregation tools
- **Traceable**: Follow single request through entire system
- **Structured**: Fields are separate, not embedded in strings

---

## APPENDIX: CONTEXT PROPAGATION FLOW

### Before (No Context)
```
POST /process
  ↓
DocumentProcessor.__init__(ai_model)
  └─ No request_id available
      └─ process_document_async()
          └─ ai_model.extract_information_async()
              └─ Logs have NO request_id
```

### After (With Context)
```
POST /process
  ↓ [RequestIDMiddleware generates UUID]
  ↓ [Sets contextvars.ContextVar]
  ↓
DocumentProcessor.__init__(ai_model)
  ├─ Reads request_id from context
  ├─ Stores self.request_id
  └─ process_document_async()
      ├─ Logs include request_id
      └─ ai_model.extract_information_async()
          ├─ Reads request_id from context
          └─ Logs include request_id
```

---

## APPENDIX: EXAMPLE LOG OUTPUT

### Single Request Trace
```
Request ID: 550e8400-e29b-41d4-a716-446655440000

2026-02-14T16:35:42.123Z [INFO] docflow.api: process_request_started request_id='550e8400-e29b-41d4-a716-446655440000' filename='invoice.pdf' model='qwen-vision'

2026-02-14T16:35:42.234Z [INFO] docflow.processor: document_processing_started request_id='550e8400-e29b-41d4-a716-446655440000' file_path='/tmp/invoice.pdf' model='qwen-vision'

2026-02-14T16:35:42.345Z [INFO] docflow.processor: text_extraction_started request_id='550e8400-e29b-41d4-a716-446655440000' file_type='pdf'

2026-02-14T16:35:42.567Z [INFO] docflow.processor: text_extraction_completed request_id='550e8400-e29b-41d4-a716-446655440000' text_length=5432

2026-02-14T16:35:42.678Z [INFO] docflow.processor: document_classification_started request_id='550e8400-e29b-41d4-a716-446655440000'

2026-02-14T16:35:42.789Z [INFO] docflow.processor: document_classification_completed request_id='550e8400-e29b-41d4-a716-446655440000' document_type='invoice' confidence=0.95

2026-02-14T16:35:42.890Z [INFO] docflow.models.qwen_vision: ai_analysis_started request_id='550e8400-e29b-41d4-a716-446655440000' model='qwen-vision' text_length=5432 has_image=True

2026-02-14T16:35:44.123Z [INFO] docflow.models.qwen_vision: ai_analysis_completed request_id='550e8400-e29b-41d4-a716-446655440000' model='qwen-vision' success=True

2026-02-14T16:35:44.234Z [INFO] docflow.processor: document_processing_completed request_id='550e8400-e29b-41d4-a716-446655440000' filename='invoice.pdf' success=True duration_ms=2111

2026-02-14T16:35:44.345Z [INFO] docflow.api: process_request_completed request_id='550e8400-e29b-41d4-a716-446655440000' status=200 duration_ms=2222
```

**Benefit**: All logs for request `550e8400-e29b-41d4-a716-446655440000` are easily identifiable and traceable!

