# Phase 2: Observability - Files to Update

**Date**: 2026-02-14  
**Total Files**: 31 (3 new, 2 modified, 26 updated)

---

## NEW FILES (3)

### 1. `docflow/middleware/__init__.py`
**Type**: New (empty init file)
**Purpose**: Make middleware a package
**Content**: Empty file (just `# Empty init file`)

### 2. `docflow/middleware/request_id.py`
**Type**: New (middleware implementation)
**Purpose**: Request ID generation and context management
**Key Components**:
- `request_id_var: contextvars.ContextVar[str]` - Context variable
- `get_request_id()` - Function to retrieve current request ID
- `RequestIDMiddleware` - FastAPI middleware class

### 3. `docflow/logging_config.py`
**Type**: New (logging configuration)
**Purpose**: structlog configuration with request ID context
**Key Components**:
- `add_request_id()` - Processor to add request_id to logs
- `configure_logging()` - Main configuration function

---

## MODIFIED FILES (2)

### 1. `requirements.txt`
**Changes**: Add structlog dependency
**Line**: After line 34 (after aiofiles)
**Add**:
```
structlog>=24.1.0
```

### 2. `docflow/api.py`
**Changes**: 
1. Add imports for middleware and logging config
2. Register RequestIDMiddleware
3. Call configure_logging() on startup

**Imports to Add**:
```python
from docflow.middleware.request_id import RequestIDMiddleware
from docflow.logging_config import configure_logging
```

**Code to Add** (before app definition):
```python
# Initialize logging
configure_logging()
```

**Middleware Registration** (before CORS):
```python
# Add RequestIDMiddleware FIRST (before CORS)
app.add_middleware(RequestIDMiddleware)
```

---

## UPDATED FILES (26)

### Core Files (2)

#### 1. `docflow/processor.py`
**Changes**:
- Add imports: `structlog`, `request_id_var`
- Update `__init__()` to accept/extract request_id
- Convert all logger calls to structlog
- Add request_id to all log calls

**Pattern**:
```python
# OLD:
logger = logging.getLogger(__name__)
logger.info(f"Available AI models: {list(self.available_models.keys())}")

# NEW:
import structlog
from docflow.middleware.request_id import request_id_var

class DocumentProcessor:
    def __init__(self, ..., request_id: Optional[str] = None):
        self.request_id = request_id or request_id_var.get()
        self.logger = structlog.get_logger(__name__)
    
    async def process_document_async(self, ...):
        self.logger.info(
            "available_models_loaded",
            request_id=self.request_id,
            models=list(self.available_models.keys()),
        )
```

#### 2. `docflow/models/__init__.py`
**Changes**:
- Add imports: `structlog`, `request_id_var`
- Update all logger calls to use structlog
- Add request_id to all log calls

---

### Model Files (13)

#### 1. `docflow/models/ollama_base.py`
**Changes**:
- Add imports: `structlog`, `request_id_var`
- Update all logger calls
- Add request_id to all log calls

#### 2. `docflow/models/openrouter_base.py`
**Changes**: Same as ollama_base.py

#### 3. `docflow/models/qwen_vision.py`
**Changes**: Same as ollama_base.py

#### 4. `docflow/models/llava.py`
**Changes**: Same as ollama_base.py

#### 5. `docflow/models/granite_vision.py`
**Changes**: Same as ollama_base.py

#### 6. `docflow/models/gemma.py`
**Changes**: Same as ollama_base.py

#### 7. `docflow/models/llama_vision.py`
**Changes**: Same as ollama_base.py

#### 8. `docflow/models/fallback.py`
**Changes**: Same as ollama_base.py

#### 9. `docflow/models/llama32_vision.py`
**Changes**: Same as ollama_base.py

#### 10. `docflow/models/olmocr_model.py`
**Changes**: Same as ollama_base.py

#### 11. `docflow/models/qwen25_vl.py`
**Changes**: Same as ollama_base.py

#### 12. `docflow/models/providers/base.py`
**Changes**: Same as ollama_base.py

#### 13. `docflow/models/providers/llama_cpp_provider.py`
**Changes**: Same as ollama_base.py

---

### Utility Files (8)

#### 1. `docflow/layout_processor.py`
**Changes**: Same as ollama_base.py

#### 2. `docflow/model_router.py`
**Changes**: Same as ollama_base.py

#### 3. `docflow/performance_optimizer.py`
**Changes**: Same as ollama_base.py

#### 4. `docflow/prompt_manager.py`
**Changes**: Same as ollama_base.py

#### 5. `docflow/response_validator.py`
**Changes**: Same as ollama_base.py

#### 6. `docflow/cli/main.py`
**Changes**: Same as ollama_base.py

#### 7. `docflow/cli/workflows.py`
**Note**: Uses `console.print()` instead of logging
**Changes**: Consider adding logging for important events

#### 8. `docflow/cli/interactive.py`
**Note**: Uses `console.print()` instead of logging
**Changes**: Consider adding logging for important events

---

## UPDATE PATTERN (For All 26 Files)

### Step 1: Add Imports
```python
import structlog
from docflow.middleware.request_id import request_id_var
```

### Step 2: Replace Logger Initialization
```python
# OLD:
logger = logging.getLogger(__name__)

# NEW:
logger = structlog.get_logger(__name__)
```

### Step 3: Update Log Calls
```python
# OLD:
logger.info(f"Processing {filename}")
logger.error(f"Failed: {error}")

# NEW:
request_id = request_id_var.get()
logger.info("processing_started", request_id=request_id, filename=filename)
logger.error("processing_failed", request_id=request_id, error=str(error), exc_info=True)
```

### Step 4: For Classes with __init__
```python
# Add to __init__:
self.request_id = request_id_var.get()
self.logger = structlog.get_logger(__name__)

# Use in methods:
self.logger.info("event_name", request_id=self.request_id, field=value)
```

---

## SUMMARY TABLE

| Category | Count | Files |
|----------|-------|-------|
| **New** | 3 | middleware/__init__.py, middleware/request_id.py, logging_config.py |
| **Modified** | 2 | requirements.txt, api.py |
| **Updated** | 26 | processor.py, models/*.py (13), utilities (8), cli/*.py (2) |
| **Total** | **31** | |

---

## IMPLEMENTATION ORDER

### Phase 1: Setup (Create new files)
1. Create `docflow/middleware/__init__.py`
2. Create `docflow/middleware/request_id.py`
3. Create `docflow/logging_config.py`

### Phase 2: Dependencies (Modify existing)
1. Update `requirements.txt`
2. Update `docflow/api.py`

### Phase 3: Core (Update high-traffic files)
1. Update `docflow/processor.py`
2. Update `docflow/models/__init__.py`

### Phase 4: Models (Update all model files)
1. Update all 13 model files

### Phase 5: Utilities (Update remaining files)
1. Update all 8 utility files
2. Update 2 CLI files

### Phase 6: Testing
1. Create tests for middleware
2. Create tests for request ID propagation
3. Run full test suite

---

## VALIDATION CHECKLIST

### Per File
- [ ] Imports added correctly
- [ ] Logger initialization updated
- [ ] All log calls converted to structlog
- [ ] request_id added to all log calls
- [ ] No syntax errors
- [ ] File still imports without errors

### Overall
- [ ] All 31 files updated
- [ ] No circular imports
- [ ] All 65 tests pass
- [ ] Logs contain request_id
- [ ] No performance regression

---

## QUICK REFERENCE: LOG CALL CONVERSION

### Pattern 1: Simple Info Log
```python
# OLD:
logger.info(f"Message with {variable}")

# NEW:
logger.info("event_name", request_id=request_id, variable=variable)
```

### Pattern 2: Error with Exception
```python
# OLD:
logger.error(f"Error: {e}")

# NEW:
logger.error("event_failed", request_id=request_id, error=str(e), exc_info=True)
```

### Pattern 3: Debug Log
```python
# OLD:
logger.debug(f"Debug info: {value}")

# NEW:
logger.debug("debug_event", request_id=request_id, value=value)
```

### Pattern 4: Warning Log
```python
# OLD:
logger.warning(f"Warning: {message}")

# NEW:
logger.warning("warning_event", request_id=request_id, message=message)
```

---

## NOTES

- **Backward Compatibility**: Old logging code still works (structlog wraps standard logging)
- **Gradual Migration**: Can update files incrementally
- **Testing**: Each file should be tested after update
- **Request ID**: Will be None if called outside request context (safe)
- **Performance**: structlog is optimized for async, minimal overhead

