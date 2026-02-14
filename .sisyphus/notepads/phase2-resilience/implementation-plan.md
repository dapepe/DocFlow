# Phase 2: Resilience - Implementation Plan

**Status**: Ready for Execution  
**Complexity**: Medium  
**Estimated Duration**: 4-6 hours  
**Dependencies**: None (all required libraries already in requirements.txt)

---

## EXECUTIVE SUMMARY

Implement a **Circuit Breaker pattern** for HTTPProvider to handle transient failures gracefully. This prevents cascading failures when downstream services are degraded.

**Key Deliverables**:
1. ✅ New `CircuitBreaker` class with state machine
2. ✅ Integration with `HTTPProvider._make_request()` and `_make_request_async()`
3. ✅ Fix missing `_get_async_client()` implementation
4. ✅ Comprehensive unit and integration tests
5. ✅ Logging for observability

---

## TASK BREAKDOWN

### TASK 1: Create CircuitBreaker Class
**File**: `docflow/models/providers/circuit_breaker.py` (NEW)  
**Complexity**: Medium  
**Time**: 1.5 hours

**Deliverables**:
- [ ] CircuitState enum (CLOSED, OPEN, HALF_OPEN)
- [ ] CircuitBreakerConfig dataclass
- [ ] CircuitBreaker class with state machine
- [ ] State transition logic
- [ ] Failure/success recording
- [ ] Logging for all state changes

**Key Methods**:
```python
class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig)
    def is_open(self) -> bool
    def is_half_open(self) -> bool
    def record_success(self)
    def record_failure(self, exception: Exception)
    def _transition_to(self, new_state: CircuitState)
```

**Testing**:
- [ ] Test CLOSED → OPEN transition
- [ ] Test OPEN → HALF_OPEN transition (after timeout)
- [ ] Test HALF_OPEN → CLOSED transition (after successes)
- [ ] Test HALF_OPEN → OPEN transition (on failure)
- [ ] Test failure counter increments
- [ ] Test success counter increments
- [ ] Test recovery timeout is respected

---

### TASK 2: Fix Async Client Implementation
**File**: `docflow/models/providers/base.py` (MODIFY)  
**Complexity**: Low  
**Time**: 0.5 hours

**Current Issues**:
- `_get_async_client()` is called but not defined
- `self.async_client` is referenced but not initialized
- No proper cleanup in `__aexit__`

**Changes Required**:
1. [ ] Add `self.async_client = None` to `HTTPProvider.__init__`
2. [ ] Implement `_get_async_client()` method
3. [ ] Use `httpx.AsyncClient` (already in requirements)
4. [ ] Add proper cleanup in `__aexit__`
5. [ ] Add logging for client creation/cleanup

**Code Template**:
```python
async def _get_async_client(self):
    """Get or create async HTTP client with connection pooling."""
    if self.async_client is None:
        import httpx
        self.async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.get("timeout", 60)),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        logger.debug("async_client_created", timeout=self.config.get("timeout", 60))
    return self.async_client
```

**Testing**:
- [ ] Async client is created on first call
- [ ] Same client is reused on subsequent calls
- [ ] Client is properly closed in `__aexit__`
- [ ] Timeout is correctly configured

---

### TASK 3: Integrate Circuit Breaker into HTTPProvider
**File**: `docflow/models/providers/base.py` (MODIFY)  
**Complexity**: Medium  
**Time**: 1.5 hours

**Changes Required**:

#### 3.1 Update HTTPProvider.__init__
```python
def __init__(self):
    super().__init__()
    self.session = None
    self.async_client = None  # NEW
    self.headers = self._setup_headers()
    self.circuit_breaker = self._create_circuit_breaker()  # NEW
```

#### 3.2 Add Circuit Breaker Configuration
```python
DEFAULT_CONFIG = {
    "timeout": 60,
    "max_retries": 3,
    "retry_backoff": 1.0,
    # Circuit Breaker Configuration
    "cb_enabled": True,
    "cb_failure_threshold": 5,
    "cb_recovery_timeout": 60,
    "cb_success_threshold": 2,
}
```

#### 3.3 Add Helper Method
```python
def _create_circuit_breaker(self):
    """Create circuit breaker with config."""
    from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
    
    config = CircuitBreakerConfig(
        failure_threshold=self.config.get("cb_failure_threshold", 5),
        recovery_timeout=self.config.get("cb_recovery_timeout", 60),
        success_threshold=self.config.get("cb_success_threshold", 2),
    )
    return CircuitBreaker(config)
```

#### 3.4 Wrap _make_request()
```python
def _make_request(self, method, url, json_data=None, **kwargs):
    """Make HTTP request with circuit breaker protection."""
    
    # Check circuit breaker
    if self.circuit_breaker.is_open():
        logger.warning("circuit_breaker_open", 
            provider=self.__class__.__name__, 
            url=url)
        raise CircuitBreakerOpenError(
            f"Circuit breaker is open for {self.__class__.__name__}"
        )
    
    session = self._get_session()
    try:
        response = session.request(
            method=method,
            url=url,
            headers=self.headers,
            json=json_data,
            timeout=self.config.get("timeout", 60),
            **kwargs,
        )
        response.raise_for_status()
        
        # Record success
        self.circuit_breaker.record_success()
        return response.json()
    
    except Exception as e:
        # Record failure
        self.circuit_breaker.record_failure(e)
        logger.error("http_request_failed",
            method=method,
            url=url,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
```

#### 3.5 Wrap _make_request_async()
```python
async def _make_request_async(self, method, url, json_data=None, **kwargs):
    """Make async HTTP request with circuit breaker protection."""
    
    # Check circuit breaker
    if self.circuit_breaker.is_open():
        logger.warning("circuit_breaker_open_async",
            provider=self.__class__.__name__,
            url=url)
        raise CircuitBreakerOpenError(
            f"Circuit breaker is open for {self.__class__.__name__}"
        )
    
    client = await self._get_async_client()
    try:
        response = await client.request(
            method=method,
            url=url,
            json=json_data,
            **kwargs
        )
        response.raise_for_status()
        
        # Record success
        self.circuit_breaker.record_success()
        return response.json()
    
    except Exception as e:
        # Record failure
        self.circuit_breaker.record_failure(e)
        logger.error("async_http_request_failed",
            method=method,
            url=url,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
```

**Testing**:
- [ ] Circuit breaker is created in __init__
- [ ] _make_request checks CB state before making request
- [ ] _make_request_async checks CB state before making request
- [ ] Successful requests record success
- [ ] Failed requests record failure
- [ ] CB state transitions are logged

---

### TASK 4: Create Exception Classes
**File**: `docflow/models/providers/circuit_breaker.py` (ADD)  
**Complexity**: Low  
**Time**: 0.25 hours

**New Exceptions**:
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

---

### TASK 5: Write Unit Tests
**File**: `tests/test_circuit_breaker.py` (NEW)  
**Complexity**: Medium  
**Time**: 1.5 hours

**Test Cases**:

#### 5.1 State Transitions
- [ ] `test_circuit_breaker_starts_closed`
- [ ] `test_circuit_breaker_opens_after_threshold`
- [ ] `test_circuit_breaker_half_opens_after_timeout`
- [ ] `test_circuit_breaker_closes_after_successes`
- [ ] `test_circuit_breaker_reopens_on_failure_in_half_open`

#### 5.2 Failure Counting
- [ ] `test_failure_count_increments`
- [ ] `test_failure_count_resets_on_success`
- [ ] `test_success_count_increments_in_half_open`
- [ ] `test_success_count_resets_on_failure`

#### 5.3 Timeout Behavior
- [ ] `test_recovery_timeout_respected`
- [ ] `test_half_open_before_timeout_not_reached`
- [ ] `test_timeout_edge_case_exactly_at_boundary`

#### 5.4 Configuration
- [ ] `test_custom_failure_threshold`
- [ ] `test_custom_recovery_timeout`
- [ ] `test_custom_success_threshold`

**Test Structure**:
```python
import pytest
from docflow.models.providers.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)

class TestCircuitBreaker:
    def test_circuit_breaker_starts_closed(self):
        cb = CircuitBreaker(CircuitBreakerConfig())
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_opens_after_threshold(self):
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)
        
        for _ in range(3):
            cb.record_failure(Exception("test"))
        
        assert cb.state == CircuitState.OPEN
        assert cb.is_open() is True
```

---

### TASK 6: Write Integration Tests
**File**: `tests/test_http_provider_circuit_breaker.py` (NEW)  
**Complexity**: Medium  
**Time**: 1.5 hours

**Test Cases**:

#### 6.1 HTTPProvider Integration
- [ ] `test_http_provider_creates_circuit_breaker`
- [ ] `test_http_provider_rejects_request_when_cb_open`
- [ ] `test_http_provider_allows_request_when_cb_closed`
- [ ] `test_http_provider_records_success_on_200`
- [ ] `test_http_provider_records_failure_on_500`

#### 6.2 Async Integration
- [ ] `test_async_http_provider_checks_cb_state`
- [ ] `test_async_http_provider_records_success`
- [ ] `test_async_http_provider_records_failure`

#### 6.3 Mock Server Tests
- [ ] `test_circuit_breaker_with_mock_server_failures`
- [ ] `test_circuit_breaker_recovery_with_mock_server`
- [ ] `test_circuit_breaker_half_open_test_request`

**Test Structure**:
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from docflow.models.providers.base import HTTPProvider

class TestHTTPProviderCircuitBreaker:
    def test_http_provider_creates_circuit_breaker(self):
        provider = ConcreteHTTPProvider()
        assert provider.circuit_breaker is not None
        assert provider.circuit_breaker.state == CircuitState.CLOSED
    
    def test_http_provider_rejects_request_when_cb_open(self):
        provider = ConcreteHTTPProvider()
        provider.circuit_breaker.state = CircuitState.OPEN
        
        with pytest.raises(CircuitBreakerOpenError):
            provider._make_request("GET", "http://example.com")
```

---

### TASK 7: Documentation & Configuration
**File**: `README.md` (MODIFY)  
**Complexity**: Low  
**Time**: 0.5 hours

**Add Section**: "Circuit Breaker Configuration"

```markdown
### Circuit Breaker Configuration

The HTTPProvider includes a built-in circuit breaker to handle transient failures:

| Setting | Default | Description |
|---------|---------|-------------|
| `cb_enabled` | `true` | Enable/disable circuit breaker |
| `cb_failure_threshold` | `5` | Failures before opening circuit |
| `cb_recovery_timeout` | `60` | Seconds before attempting recovery |
| `cb_success_threshold` | `2` | Successes in HALF_OPEN before closing |

**Example Configuration**:
```python
config = {
    "cb_enabled": True,
    "cb_failure_threshold": 5,
    "cb_recovery_timeout": 60,
    "cb_success_threshold": 2,
}
```

**States**:
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, requests rejected immediately
- **HALF_OPEN**: Testing recovery, single request allowed
```

---

## EXECUTION CHECKLIST

### Pre-Implementation
- [ ] Read and understand circuit-breaker-analysis.md
- [ ] Review HTTPProvider architecture
- [ ] Check httpx documentation for AsyncClient
- [ ] Verify structlog is available

### Implementation
- [ ] Task 1: Create CircuitBreaker class
- [ ] Task 2: Fix async client implementation
- [ ] Task 3: Integrate CB into HTTPProvider
- [ ] Task 4: Create exception classes
- [ ] Task 5: Write unit tests
- [ ] Task 6: Write integration tests
- [ ] Task 7: Update documentation

### Verification
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No LSP errors in modified files
- [ ] Code coverage > 85%
- [ ] Logging shows state transitions
- [ ] No new external dependencies

### Cleanup
- [ ] Run `pytest tests/` - all pass
- [ ] Run `lsp_diagnostics` on modified files
- [ ] Commit changes with atomic commits
- [ ] Update AGENTS.md if needed

---

## RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Async client breaks existing code | Low | High | Comprehensive async tests |
| State machine race conditions | Medium | High | Use locks for thread safety |
| Configuration not flexible | Low | Medium | Make all thresholds configurable |
| Performance impact | Low | Medium | Benchmark before/after |

---

## SUCCESS CRITERIA

✅ **All of the following must be true**:

1. CircuitBreaker class exists with full state machine
2. HTTPProvider integrates CB for sync and async
3. Async client properly implemented and tested
4. All unit tests pass (>85% coverage)
5. All integration tests pass
6. Logging shows state transitions clearly
7. Configuration is flexible and documented
8. No new external dependencies added
9. No LSP errors in modified files
10. Code follows project conventions (structlog, etc.)

---

## ESTIMATED TIMELINE

| Task | Hours | Status |
|------|-------|--------|
| Task 1: CircuitBreaker class | 1.5 | Pending |
| Task 2: Async client fix | 0.5 | Pending |
| Task 3: CB integration | 1.5 | Pending |
| Task 4: Exception classes | 0.25 | Pending |
| Task 5: Unit tests | 1.5 | Pending |
| Task 6: Integration tests | 1.5 | Pending |
| Task 7: Documentation | 0.5 | Pending |
| **TOTAL** | **7.25** | **Pending** |

---

## NOTES

- All required libraries (httpx, structlog) already in requirements.txt
- No breaking changes to existing API
- Circuit breaker can be disabled via config if needed
- Thread safety should be considered for multi-threaded deployments
- Consider adding metrics/monitoring in future phase

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-14  
**Author**: Sisyphus-Junior
