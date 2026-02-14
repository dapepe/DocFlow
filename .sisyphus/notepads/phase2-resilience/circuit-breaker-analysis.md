# Phase 2: Resilience (Circuit Breaker) - Analysis & Implementation Plan

**Date**: 2026-02-14  
**Status**: Analysis Complete  
**Task**: Prepare Circuit Breaker implementation for HTTPProvider

---

## 1. CURRENT STATE ANALYSIS

### 1.1 HTTPProvider Architecture

**Location**: `docflow/models/providers/base.py` (lines 172-297)

**Current Capabilities**:
- ✅ Connection pooling via `requests.Session()`
- ✅ Retry logic via `urllib3.Retry` (max 3 retries, backoff 1.0)
- ✅ Status code handling (429, 500, 502, 503, 504)
- ✅ Timeout configuration (default 60s)
- ✅ Async support (partial - `_make_request_async` exists but `_get_async_client` is NOT implemented)

**Current Request Methods**:
```python
# Sync: _make_request(method, url, json_data, **kwargs)
# Async: _make_request_async(method, url, json_data, **kwargs)
```

### 1.2 Missing Pieces

**Critical Issues**:
1. ❌ `_get_async_client()` is called but NOT defined (lines 235, 250)
2. ❌ `self.async_client` is referenced but never initialized (lines 255-257)
3. ❌ No Circuit Breaker pattern implemented
4. ❌ No fallback/degradation strategy
5. ❌ No health check mechanism

### 1.3 Dependencies Analysis

**Current Dependencies** (from `requirements.txt`):
- ✅ `requests>=2.31.0` - Sync HTTP
- ✅ `httpx>=0.27.0` - Async HTTP (installed but not used)
- ✅ `aiohttp>=3.9.0` - Alternative async HTTP
- ❌ `tenacity` - NOT installed (popular retry library)
- ❌ `pybreaker` - NOT installed (circuit breaker library)

**Recommendation**: Use `httpx` (already in requirements) for async + implement custom lightweight Circuit Breaker

---

## 2. CIRCUIT BREAKER DESIGN

### 2.1 State Machine

```
CLOSED (normal operation)
  ↓ (failure threshold exceeded)
OPEN (reject requests immediately)
  ↓ (timeout elapsed)
HALF_OPEN (test single request)
  ↓ (success) → CLOSED
  ↓ (failure) → OPEN
```

### 2.2 Configuration Parameters

```python
CircuitBreakerConfig:
  failure_threshold: int = 5          # Failures before OPEN
  recovery_timeout: int = 60          # Seconds before HALF_OPEN
  success_threshold: int = 2          # Successes in HALF_OPEN before CLOSED
  monitored_exceptions: List[Type]    # Which exceptions trigger circuit
  excluded_status_codes: List[int]    # Status codes that don't count as failures
```

### 2.3 Failure Detection Strategy

**Count as Failures**:
- Connection timeouts
- Connection refused
- HTTP 500, 502, 503, 504 (server errors)
- HTTP 429 (rate limit - after retries exhausted)

**Do NOT Count as Failures**:
- HTTP 400, 401, 403, 404 (client errors - not transient)
- HTTP 200-299 (success)
- Successful HALF_OPEN test

---

## 3. IMPLEMENTATION STRATEGY

### 3.1 New Files to Create

```
docflow/models/providers/
├── circuit_breaker.py          # NEW: CircuitBreaker class
└── base.py                     # MODIFY: Add CB to HTTPProvider
```

### 3.2 CircuitBreaker Class Structure

```python
class CircuitBreaker:
    """Lightweight circuit breaker for HTTP providers."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.state = "CLOSED"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.config = config
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        # Check state and decide: allow, reject, or test
        # Update counters based on result
        # Transition states as needed
    
    def record_success(self):
        """Record successful call."""
    
    def record_failure(self, exception):
        """Record failed call."""
    
    def is_open(self) -> bool:
        """Check if circuit is open."""
    
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
```

### 3.3 HTTPProvider Integration Points

**Modify `_make_request()`**:
```python
def _make_request(self, method, url, json_data=None, **kwargs):
    try:
        # Check circuit breaker state
        if self.circuit_breaker.is_open():
            raise CircuitBreakerOpenError(...)
        
        # Make request (existing logic)
        response = session.request(...)
        
        # Record success
        self.circuit_breaker.record_success()
        return response.json()
    
    except Exception as e:
        # Record failure
        self.circuit_breaker.record_failure(e)
        raise
```

**Modify `_make_request_async()`**:
```python
async def _make_request_async(self, method, url, json_data=None, **kwargs):
    try:
        # Check circuit breaker state
        if self.circuit_breaker.is_open():
            raise CircuitBreakerOpenError(...)
        
        # Make async request
        response = await client.request(...)
        
        # Record success
        self.circuit_breaker.record_success()
        return response.json()
    
    except Exception as e:
        # Record failure
        self.circuit_breaker.record_failure(e)
        raise
```

### 3.4 Async Client Implementation (CRITICAL FIX)

**Add to HTTPProvider**:
```python
async def _get_async_client(self):
    """Get or create async HTTP client."""
    if self.async_client is None:
        import httpx
        self.async_client = httpx.AsyncClient(
            timeout=self.config.get("timeout", 60),
            limits=httpx.Limits(max_connections=10)
        )
    return self.async_client
```

---

## 4. IMPLEMENTATION PHASES

### Phase 4.1: Create CircuitBreaker Class
- [ ] Create `docflow/models/providers/circuit_breaker.py`
- [ ] Implement state machine logic
- [ ] Add configuration class
- [ ] Add logging for state transitions
- [ ] Write unit tests

### Phase 4.2: Fix Async Client
- [ ] Implement `_get_async_client()` in HTTPProvider
- [ ] Initialize `self.async_client = None` in `__init__`
- [ ] Add proper cleanup in `__aexit__`
- [ ] Test async context manager

### Phase 4.3: Integrate Circuit Breaker
- [ ] Add `self.circuit_breaker` to HTTPProvider `__init__`
- [ ] Wrap `_make_request()` with CB logic
- [ ] Wrap `_make_request_async()` with CB logic
- [ ] Add CB configuration to DEFAULT_CONFIG
- [ ] Add logging for CB state changes

### Phase 4.4: Testing & Validation
- [ ] Unit tests for CircuitBreaker state transitions
- [ ] Integration tests with mock HTTP server
- [ ] Test failure threshold behavior
- [ ] Test recovery timeout behavior
- [ ] Test HALF_OPEN state transitions

---

## 5. ERROR HANDLING STRATEGY

### 5.1 New Exception Classes

```python
class CircuitBreakerError(Exception):
    """Base exception for circuit breaker."""
    pass

class CircuitBreakerOpenError(CircuitBreakerError):
    """Circuit is open, rejecting requests."""
    pass

class CircuitBreakerHalfOpenError(CircuitBreakerError):
    """Circuit is half-open, testing recovery."""
    pass
```

### 5.2 Failure Classification

```python
def should_count_as_failure(exception, status_code):
    """Determine if exception should increment failure counter."""
    
    # Client errors (4xx) - NOT failures
    if 400 <= status_code < 500:
        return False
    
    # Server errors (5xx) - ARE failures
    if 500 <= status_code < 600:
        return True
    
    # Network errors - ARE failures
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True
    
    return False
```

---

## 6. LOGGING STRATEGY

**Log Circuit Breaker Events**:
```python
logger.info("circuit_breaker_state_change", 
    old_state="CLOSED", 
    new_state="OPEN",
    failure_count=5,
    provider=self.__class__.__name__)

logger.warning("circuit_breaker_open",
    provider=self.__class__.__name__,
    recovery_timeout=60)

logger.info("circuit_breaker_half_open",
    provider=self.__class__.__name__)
```

---

## 7. CONFIGURATION EXAMPLE

```python
# In HTTPProvider.DEFAULT_CONFIG
DEFAULT_CONFIG = {
    "timeout": 60,
    "max_retries": 3,
    "retry_backoff": 1.0,
    # Circuit Breaker
    "cb_failure_threshold": 5,
    "cb_recovery_timeout": 60,
    "cb_success_threshold": 2,
}
```

---

## 8. TESTING CHECKLIST

### Unit Tests
- [ ] CircuitBreaker state transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- [ ] Failure counter increments correctly
- [ ] Success counter increments correctly
- [ ] Recovery timeout is respected
- [ ] Excluded status codes don't trigger failures

### Integration Tests
- [ ] HTTPProvider with CB enabled
- [ ] Async client creation and cleanup
- [ ] Request succeeds when CB is CLOSED
- [ ] Request rejected when CB is OPEN
- [ ] Recovery works after timeout

### Edge Cases
- [ ] Multiple concurrent requests during HALF_OPEN
- [ ] Rapid state transitions
- [ ] Timeout edge cases (exactly at boundary)
- [ ] Exception types not in monitored list

---

## 9. DEPENDENCIES & IMPORTS

**No new external dependencies needed**:
- `httpx` already in requirements.txt
- `structlog` already in use
- Standard library: `time`, `threading`, `enum`

**Imports for circuit_breaker.py**:
```python
from enum import Enum
from typing import Callable, Type, List, Optional, Any
from dataclasses import dataclass
from time import time
import structlog

logger = structlog.get_logger(__name__)
```

---

## 10. RISK ASSESSMENT

### Low Risk
- ✅ No new external dependencies
- ✅ Backward compatible (CB can be disabled)
- ✅ Isolated in new file
- ✅ Existing retry logic still works

### Medium Risk
- ⚠️ Async client implementation (currently broken)
- ⚠️ State machine complexity
- ⚠️ Thread safety (if used in multi-threaded context)

### Mitigation
- Comprehensive unit tests
- Logging at every state transition
- Configuration to disable CB if needed
- Thread-safe implementation using locks

---

## 11. SUCCESS CRITERIA

✅ **Phase 2 Resilience Complete When**:
1. CircuitBreaker class implemented with full state machine
2. HTTPProvider integrates CB for both sync and async
3. Async client properly implemented and tested
4. All unit tests pass (>90% coverage)
5. Integration tests pass with mock HTTP server
6. Logging shows state transitions clearly
7. Configuration is flexible and documented
8. No new external dependencies added

---

## 12. NEXT STEPS

1. **Create circuit_breaker.py** with CircuitBreaker class
2. **Fix async client** in HTTPProvider
3. **Integrate CB** into _make_request and _make_request_async
4. **Write comprehensive tests**
5. **Document configuration** in README
6. **Verify with real providers** (OpenAI, Anthropic, etc.)

---

## APPENDIX: Code Snippets

### A1. CircuitBreaker Skeleton

```python
from enum import Enum
from time import time
from typing import Callable, Type, List, Optional, Any
import structlog

logger = structlog.get_logger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60, success_threshold=2):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
    
    def is_open(self) -> bool:
        if self.state == CircuitState.OPEN:
            if time() - self.last_failure_time > self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return False
            return True
        return False
    
    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        self.last_failure_time = time()
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)
    
    def _transition_to(self, new_state: CircuitState):
        old_state = self.state
        self.state = new_state
        logger.info("circuit_breaker_transition", 
            old_state=old_state.value, 
            new_state=new_state.value)
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-14  
**Author**: Sisyphus-Junior
