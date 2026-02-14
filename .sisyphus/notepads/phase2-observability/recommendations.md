# Phase 2: Observability - Implementation Recommendations

**Date**: 2026-02-14  
**Prepared For**: Phase 2.2 (Structured Logging & Request ID Tracing)

## EXECUTIVE RECOMMENDATIONS

### 1. Use structlog (NOT python-json-logger)
**Why**:
- Native async support (critical for FastAPI)
- Structured field logging (not string interpolation)
- Built-in contextvars support
- Minimal performance overhead
- Integrates seamlessly with standard logging

**Version**: `structlog>=24.1.0`

### 2. Use contextvars for Request ID (NOT thread-local)
**Why**:
- Async-safe (thread-local breaks with async)
- Works across await boundaries
- Automatic cleanup
- Standard library (no dependency)

**Pattern**:
```python
import contextvars
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default=None)
```

### 3. Implement RequestIDMiddleware (NOT decorator)
**Why**:
- Applies to ALL endpoints automatically
- Handles request ID generation
- Sets response header for client tracking
- Proper async context management

**Location**: `docflow/middleware/request_id.py`

### 4. Keep Backward Compatibility
**Why**:
- Existing code uses `logging.getLogger()`
- structlog wraps standard logging
- No breaking changes to existing code
- Gradual migration possible

**Pattern**:
```python
# Old code still works
logger = logging.getLogger(__name__)
logger.info("message")

# New code uses structlog
logger = structlog.get_logger(__name__)
logger.info("message", request_id=request_id, field=value)
```

## DETAILED IMPLEMENTATION PLAN

### Step 1: Add Dependencies
**File**: `requirements.txt`

Add after line 34 (after aiofiles):
```
structlog>=24.1.0
```

Optional (for JSON output):
```
python-json-logger>=2.0.7
```

### Step 2: Create Request ID Middleware
**File**: `docflow/middleware/__init__.py` (new)
```python
# Empty init file
```

**File**: `docflow/middleware/request_id.py` (new)
```python
"""Request ID middleware for request tracing."""

import uuid
import contextvars
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Context variable for request ID (async-safe)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    'request_id', default=None
)

def get_request_id() -> str:
    """Get current request ID from context."""
    return request_id_var.get()

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to inject and track request IDs."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with request ID."""
        # Generate or extract request ID
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
        # Set in context (async-safe)
        token = request_id_var.set(request_id)
        
        try:
            # Process request
            response = await call_next(request)
            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id
            return response
        finally:
            # Clean up context
            request_id_var.reset(token)
```

### Step 3: Create Logging Configuration
**File**: `docflow/logging_config.py` (new)
```python
"""Structured logging configuration with request ID context."""

import structlog
import logging
from docflow.middleware.request_id import request_id_var

def add_request_id(logger, method_name, event_dict):
    """Add request ID to all log events."""
    request_id = request_id_var.get()
    if request_id:
        event_dict['request_id'] = request_id
    return event_dict

def configure_logging(log_level: str = "INFO"):
    """Configure structlog with request ID context."""
    
    structlog.configure(
        processors=[
            # Filter by log level
            structlog.stdlib.filter_by_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add log level
            structlog.stdlib.add_log_level,
            # Add request ID from context
            add_request_id,
            # Format positional arguments
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add stack info for exceptions
            structlog.processors.StackInfoRenderer(),
            # Format exceptions
            structlog.processors.format_exc_info,
            # Decode unicode
            structlog.processors.UnicodeDecoder(),
            # Wrap for standard logging
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=[logging.StreamHandler()],
    )
```

### Step 4: Update API
**File**: `docflow/api.py`

**Changes**:
1. Add imports at top:
```python
from docflow.middleware.request_id import RequestIDMiddleware
from docflow.logging_config import configure_logging
```

2. Register middleware BEFORE CORS (order matters):
```python
# Initialize logging
configure_logging()

app = FastAPI(...)

# Add RequestIDMiddleware FIRST (before CORS)
app.add_middleware(RequestIDMiddleware)

# Then add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Step 5: Update Processor
**File**: `docflow/processor.py`

**Changes**:
1. Add imports:
```python
import structlog
from docflow.middleware.request_id import request_id_var
```

2. Update `__init__`:
```python
def __init__(
    self,
    rules_file: str = "config/default_rules.yaml",
    ai_model: Optional[str] = None,
    request_id: Optional[str] = None,
):
    self.request_id = request_id or request_id_var.get()
    self.logger = structlog.get_logger(__name__)
    # ... rest of init
```

3. Update log calls (example):
```python
# OLD:
logger.info(f"Available AI models: {list(self.available_models.keys())}")

# NEW:
self.logger.info(
    "available_models_loaded",
    request_id=self.request_id,
    models=list(self.available_models.keys()),
    count=len(self.available_models),
)
```

### Step 6: Update Models
**Pattern for all model classes**:

```python
import structlog
from docflow.middleware.request_id import request_id_var

class QwenVisionModel(BaseModel):
    async def extract_information_async(self, text: str, image_path: Optional[str] = None):
        logger = structlog.get_logger(__name__)
        request_id = request_id_var.get()
        
        logger.info(
            "ai_analysis_started",
            request_id=request_id,
            model=self.model_id,
            text_length=len(text),
            has_image=image_path is not None,
        )
        
        try:
            result = await self._analyze(text, image_path)
            logger.info(
                "ai_analysis_completed",
                request_id=request_id,
                model=self.model_id,
                success=True,
            )
            return result
        except Exception as e:
            logger.error(
                "ai_analysis_failed",
                request_id=request_id,
                model=self.model_id,
                error=str(e),
                exc_info=True,
            )
            raise
```

## LOGGING BEST PRACTICES

### Event Names (NOT messages)
```python
# BAD: String message
logger.info(f"Processing document {filename}")

# GOOD: Event name + structured fields
logger.info("document_processing_started", filename=filename)
```

### Structured Fields
```python
# BAD: Everything in string
logger.error(f"Failed to process {file} with model {model}: {error}")

# GOOD: Separate fields
logger.error(
    "document_processing_failed",
    file=file,
    model=model,
    error=str(error),
    exc_info=True,
)
```

### Request ID in All Logs
```python
# Always include request_id
logger.info(
    "event_name",
    request_id=request_id,  # ALWAYS
    field1=value1,
    field2=value2,
)
```

### Exception Handling
```python
# Use exc_info=True for full traceback
try:
    risky_operation()
except Exception as e:
    logger.error(
        "operation_failed",
        request_id=request_id,
        error=str(e),
        exc_info=True,  # Includes full traceback
    )
    raise
```

## TESTING STRATEGY

### Test 1: RequestIDMiddleware
```python
def test_request_id_middleware():
    """Verify request ID is generated and propagated."""
    # Test that middleware generates UUID
    # Test that middleware sets response header
    # Test that context variable is set
```

### Test 2: Request ID Propagation
```python
def test_request_id_in_processor():
    """Verify request ID flows through processor."""
    # Create processor with request_id
    # Verify processor stores request_id
    # Verify logs contain request_id
```

### Test 3: Structured Log Format
```python
def test_structured_log_format():
    """Verify logs are properly structured."""
    # Capture log output
    # Verify JSON format (if using JSON formatter)
    # Verify all expected fields present
```

## MIGRATION STRATEGY

### Phase 1: Setup (No Breaking Changes)
- Add structlog dependency
- Create middleware and config
- Register middleware in API
- Existing code still works

### Phase 2: Gradual Migration
- Update high-traffic paths first (processor, models)
- Update utilities later
- Keep backward compatibility

### Phase 3: Cleanup (Optional)
- Remove old logging patterns
- Standardize on structlog
- Add JSON formatter for production

## EXPECTED LOG OUTPUT

### Before (Current)
```
2026-02-14 16:35:42,123 - docflow.processor - INFO - Available AI models: ['qwen-vision', 'granite-vision']
2026-02-14 16:35:43,456 - docflow.models.qwen_vision - INFO - Initialized Qwen Vision model
2026-02-14 16:35:44,789 - docflow.processor - INFO - Successfully processed document: invoice.pdf
```

### After (Structured)
```
2026-02-14T16:35:42.123Z [INFO] docflow.processor: available_models_loaded request_id='550e8400-e29b-41d4-a716-446655440000' models=['qwen-vision', 'granite-vision'] count=2
2026-02-14T16:35:43.456Z [INFO] docflow.models.qwen_vision: ai_analysis_started request_id='550e8400-e29b-41d4-a716-446655440000' model='qwen-vision' text_length=5432 has_image=True
2026-02-14T16:35:44.789Z [INFO] docflow.processor: document_processing_completed request_id='550e8400-e29b-41d4-a716-446655440000' filename='invoice.pdf' success=True duration_ms=2666
```

### With JSON Formatter (Optional)
```json
{"timestamp": "2026-02-14T16:35:42.123Z", "level": "info", "logger": "docflow.processor", "message": "available_models_loaded", "request_id": "550e8400-e29b-41d4-a716-446655440000", "models": ["qwen-vision", "granite-vision"], "count": 2}
{"timestamp": "2026-02-14T16:35:43.456Z", "level": "info", "logger": "docflow.models.qwen_vision", "message": "ai_analysis_started", "request_id": "550e8400-e29b-41d4-a716-446655440000", "model": "qwen-vision", "text_length": 5432, "has_image": true}
{"timestamp": "2026-02-14T16:35:44.789Z", "level": "info", "logger": "docflow.processor", "message": "document_processing_completed", "request_id": "550e8400-e29b-41d4-a716-446655440000", "filename": "invoice.pdf", "success": true, "duration_ms": 2666}
```

## RISK MITIGATION

| Risk | Mitigation |
|------|-----------|
| structlog version conflicts | Pin version in requirements.txt |
| Async context issues | Use contextvars properly, test thoroughly |
| Performance overhead | structlog is optimized, minimal impact |
| Breaking changes | Keep backward compatibility with standard logging |
| Missing request_id in logs | Add request_id to all log calls |

## VALIDATION CHECKLIST

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

## FILES TO CREATE/MODIFY

### Create (3 files)
- `docflow/middleware/__init__.py` (empty)
- `docflow/middleware/request_id.py` (RequestIDMiddleware)
- `docflow/logging_config.py` (structlog configuration)

### Modify (2 files)
- `requirements.txt` (add structlog)
- `docflow/api.py` (register middleware, configure logging)

### Update (26 files)
- `docflow/processor.py` (add request_id support)
- All 13 model files (use structlog)
- All utility files (use structlog)

## EFFORT BREAKDOWN

| Task | Files | Effort | Notes |
|------|-------|--------|-------|
| Setup | 3 new | 1 hour | Middleware, config, dependencies |
| API | 1 | 30 min | Register middleware |
| Processor | 1 | 1 hour | Add request_id, update logs |
| Models | 13 | 2 hours | Repetitive pattern |
| Utilities | 8 | 1 hour | Similar to models |
| Testing | - | 1 hour | New tests + validation |
| **Total** | **26** | **6-7 hours** | Sequential execution |

