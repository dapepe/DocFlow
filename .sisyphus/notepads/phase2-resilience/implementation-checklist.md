# Phase 2: Resilience (Rate Limiting) - Implementation Checklist

**Date**: 2026-02-14  
**Status**: Ready for Implementation  
**Estimated Duration**: 4-6 hours

---

## TASK 1: Create docflow/rate_limiter.py

### Deliverable
New file: `docflow/rate_limiter.py` (~150 lines)

### Checklist

- [ ] **Create file structure**
  - [ ] Module docstring explaining rate limiting
  - [ ] Imports: `asyncio`, `threading`, `time`, `structlog`
  - [ ] Logger setup: `logger = structlog.get_logger(__name__)`

- [ ] **Implement RateLimitError exception**
  - [ ] Inherits from `Exception`
  - [ ] Constructor takes `retry_after: float`
  - [ ] Stores `self.retry_after`
  - [ ] Message format: `"Rate limited. Retry after {retry_after:.2f}s"`

- [ ] **Implement TokenBucket class**
  - [ ] Constructor: `__init__(self, capacity: int, refill_rate: float)`
  - [ ] Instance variables:
    - [ ] `self._capacity: int`
    - [ ] `self._refill_rate: float`
    - [ ] `self._tokens: float` (initialized to capacity)
    - [ ] `self._last_refill: float` (time.monotonic())
    - [ ] `self._sync_lock: threading.Lock`
    - [ ] `self._async_lock: Optional[asyncio.Lock]` (None initially)

  - [ ] Method: `_refill(self) -> None`
    - [ ] Calculate elapsed time since last refill
    - [ ] Update tokens: `min(capacity, tokens + elapsed * refill_rate)`
    - [ ] Update `_last_refill` to current time
    - [ ] No logging (internal method)

  - [ ] Method: `try_acquire(self, cost: float = 1.0) -> bool`
    - [ ] Use `with self._sync_lock:`
    - [ ] Call `self._refill()`
    - [ ] Check if `self._tokens >= cost`
    - [ ] If yes: decrement tokens, return True
    - [ ] If no: return False
    - [ ] No logging (caller logs)

  - [ ] Method: `async try_acquire_async(self, cost: float = 1.0) -> bool`
    - [ ] Lazy init async lock: `if self._async_lock is None: self._async_lock = asyncio.Lock()`
    - [ ] Use `async with self._async_lock:`
    - [ ] Call `self._refill()`
    - [ ] Check if `self._tokens >= cost`
    - [ ] If yes: decrement tokens, return True
    - [ ] If no: return False
    - [ ] No logging (caller logs)

  - [ ] Method: `get_retry_after(self, cost: float = 1.0) -> float`
    - [ ] Use `with self._sync_lock:`
    - [ ] Call `self._refill()`
    - [ ] If `self._tokens >= cost`: return 0.0
    - [ ] Else: calculate deficit and return `deficit / self._refill_rate`
    - [ ] Used by caller to determine wait time

- [ ] **Add comprehensive docstrings**
  - [ ] Module docstring
  - [ ] RateLimitError docstring
  - [ ] TokenBucket class docstring
  - [ ] Each method docstring with Args, Returns, Raises

- [ ] **Add __all__ export**
  - [ ] `__all__ = ["TokenBucket", "RateLimitError"]`

### Verification
```bash
python -c "from docflow.rate_limiter import TokenBucket, RateLimitError; print('OK')"
```

---

## TASK 2: Integrate into HTTPProvider

### Files to Modify
- `docflow/models/providers/base.py`

### Checklist

- [ ] **Add import at top of file**
  - [ ] After existing imports, add:
    ```python
    from docflow.rate_limiter import TokenBucket, RateLimitError
    ```

- [ ] **Update HTTPProvider.DEFAULT_CONFIG**
  - [ ] Add two new keys:
    ```python
    DEFAULT_CONFIG = {
        "timeout": 60,
        "max_retries": 3,
        "retry_backoff": 1.0,
        "rate_limit_capacity": 100,      # NEW
        "rate_limit_refill_rate": 10.0,  # NEW
    }
    ```

- [ ] **Update HTTPProvider.__init__**
  - [ ] After `self.circuit_breaker = CircuitBreaker()`, add:
    ```python
    self.rate_limiter = TokenBucket(
        capacity=self.config.get("rate_limit_capacity", 100),
        refill_rate=self.config.get("rate_limit_refill_rate", 10.0),
    )
    ```
  - [ ] Add logging: `logger.debug("rate_limiter_initialized", capacity=..., refill_rate=...)`

- [ ] **Update _make_request() method**
  - [ ] Add rate limit check BEFORE circuit breaker check:
    ```python
    # Check rate limit
    if not self.rate_limiter.try_acquire():
        retry_after = self.rate_limiter.get_retry_after()
        logger.warning("rate_limit_exceeded", retry_after=retry_after)
        raise RateLimitError(retry_after)
    ```
  - [ ] Keep existing circuit breaker check
  - [ ] Keep existing request logic

- [ ] **Update _make_request_async() method**
  - [ ] Add rate limit check BEFORE circuit breaker check:
    ```python
    # Check rate limit
    if not await self.rate_limiter.try_acquire_async():
        retry_after = self.rate_limiter.get_retry_after()
        logger.warning("rate_limit_exceeded", retry_after=retry_after)
        raise RateLimitError(retry_after)
    ```
  - [ ] Keep existing circuit breaker check
  - [ ] Keep existing request logic

- [ ] **Update docstrings**
  - [ ] Add rate limiting to HTTPProvider class docstring
  - [ ] Update _make_request docstring to mention rate limiting
  - [ ] Update _make_request_async docstring to mention rate limiting

### Verification
```bash
python -c "from docflow.models.providers.base import HTTPProvider; print('OK')"
python -c "from docflow.models import ModelRegistry; print('OK')"
```

---

## TASK 3: Write Unit Tests

### File to Create
- `tests/test_rate_limiter.py` (~200 lines)

### Checklist

- [ ] **Test imports**
  - [ ] Import TokenBucket, RateLimitError
  - [ ] Import time, asyncio, threading
  - [ ] Import pytest

- [ ] **Test RateLimitError**
  - [ ] Test constructor with retry_after
  - [ ] Test message format
  - [ ] Test exception inheritance

- [ ] **Test TokenBucket initialization**
  - [ ] Test with default parameters
  - [ ] Test with custom capacity and refill_rate
  - [ ] Verify initial tokens equal capacity

- [ ] **Test _refill() logic**
  - [ ] Test refill calculation with elapsed time
  - [ ] Test refill doesn't exceed capacity
  - [ ] Test refill with zero elapsed time

- [ ] **Test try_acquire() - Sync**
  - [ ] Test acquire when tokens available
  - [ ] Test acquire when tokens not available
  - [ ] Test multiple acquisitions
  - [ ] Test refill between acquisitions
  - [ ] Test cost parameter (acquire 2 tokens)

- [ ] **Test try_acquire_async() - Async**
  - [ ] Test acquire when tokens available
  - [ ] Test acquire when tokens not available
  - [ ] Test multiple acquisitions
  - [ ] Test refill between acquisitions
  - [ ] Test cost parameter (acquire 2 tokens)

- [ ] **Test get_retry_after()**
  - [ ] Test when tokens available (returns 0.0)
  - [ ] Test when tokens not available (returns > 0)
  - [ ] Test calculation accuracy

- [ ] **Test concurrent access - Sync**
  - [ ] Create multiple threads
  - [ ] Each thread tries to acquire tokens
  - [ ] Verify no race conditions
  - [ ] Verify total tokens consumed is correct

- [ ] **Test concurrent access - Async**
  - [ ] Create multiple coroutines
  - [ ] Each coroutine tries to acquire tokens
  - [ ] Verify no race conditions
  - [ ] Verify total tokens consumed is correct

- [ ] **Test edge cases**
  - [ ] Capacity = 1, refill_rate = 0.1
  - [ ] Very high refill_rate
  - [ ] Cost > capacity
  - [ ] Negative cost (should fail or be handled)

### Verification
```bash
pytest tests/test_rate_limiter.py -v
```

---

## TASK 4: Write Integration Tests

### File to Create
- `tests/test_http_provider_rate_limit.py` (~150 lines)

### Checklist

- [ ] **Test imports**
  - [ ] Import HTTPProvider (or a concrete subclass)
  - [ ] Import RateLimitError
  - [ ] Import pytest, unittest.mock

- [ ] **Test HTTPProvider initialization**
  - [ ] Verify rate_limiter is created
  - [ ] Verify config values are used
  - [ ] Verify default values are applied

- [ ] **Test _make_request() with rate limiting**
  - [ ] Mock requests.Session.request
  - [ ] Test successful request (rate limit OK)
  - [ ] Test rate limited request (raises RateLimitError)
  - [ ] Verify retry_after is set correctly

- [ ] **Test _make_request_async() with rate limiting**
  - [ ] Mock httpx.AsyncClient.request
  - [ ] Test successful request (rate limit OK)
  - [ ] Test rate limited request (raises RateLimitError)
  - [ ] Verify retry_after is set correctly

- [ ] **Test circuit breaker + rate limiter interaction**
  - [ ] Rate limit checked first
  - [ ] Circuit breaker checked second
  - [ ] Both can raise independently
  - [ ] Correct exception type raised

- [ ] **Test logging**
  - [ ] Verify rate_limit_exceeded is logged
  - [ ] Verify retry_after is included in log
  - [ ] Verify rate_limiter_initialized is logged

- [ ] **Test configuration override**
  - [ ] Create HTTPProvider subclass with custom config
  - [ ] Verify custom capacity is used
  - [ ] Verify custom refill_rate is used

### Verification
```bash
pytest tests/test_http_provider_rate_limit.py -v
```

---

## TASK 5: Run Full Test Suite

### Checklist

- [ ] **Run all tests**
  ```bash
  pytest tests/ -v
  ```

- [ ] **Verify results**
  - [ ] All existing tests still pass (65 tests)
  - [ ] New rate limiter tests pass
  - [ ] New integration tests pass
  - [ ] No regressions

- [ ] **Check for import errors**
  ```bash
  python -c "from docflow.models import ModelRegistry; print('OK')"
  python -c "from docflow.models.providers.base import HTTPProvider; print('OK')"
  python -c "from docflow.rate_limiter import TokenBucket; print('OK')"
  ```

- [ ] **Check for syntax errors**
  ```bash
  python -m py_compile docflow/rate_limiter.py
  python -m py_compile docflow/models/providers/base.py
  ```

### Verification
```bash
pytest tests/ -v --tb=short
```

---

## TASK 6: Update Documentation

### Files to Update
- `docflow/models/providers/AGENTS.md`

### Checklist

- [ ] **Add rate limiting section to AGENTS.md**
  - [ ] Explain TokenBucket algorithm
  - [ ] Document configuration options
  - [ ] Show example configurations
  - [ ] Explain interaction with circuit breaker

- [ ] **Update HTTPProvider docstring**
  - [ ] Add rate limiting to capabilities list
  - [ ] Document DEFAULT_CONFIG keys

- [ ] **Add code examples**
  - [ ] Default configuration example
  - [ ] Per-provider override example
  - [ ] Environment variable override example

### Verification
```bash
grep -n "rate_limit" docflow/models/providers/AGENTS.md
```

---

## TASK 7: Create Beads for Phase 2.2

### Checklist

- [ ] **Create epic for Phase 2.2**
  ```bash
  bd create --type=epic --title="Phase 2.2: Rate Limiting" --priority=1
  ```

- [ ] **Create task for rate_limiter.py**
  ```bash
  bd create --type=task --title="Implement TokenBucket rate limiter" --priority=1 --parent=<epic-id>
  ```

- [ ] **Create task for HTTPProvider integration**
  ```bash
  bd create --type=task --title="Integrate rate limiter into HTTPProvider" --priority=1 --parent=<epic-id>
  ```

- [ ] **Create task for unit tests**
  ```bash
  bd create --type=task --title="Write unit tests for rate limiter" --priority=1 --parent=<epic-id>
  ```

- [ ] **Create task for integration tests**
  ```bash
  bd create --type=task --title="Write integration tests for HTTPProvider" --priority=1 --parent=<epic-id>
  ```

- [ ] **Create task for documentation**
  ```bash
  bd create --type=task --title="Update documentation for rate limiting" --priority=2 --parent=<epic-id>
  ```

- [ ] **Sync beads**
  ```bash
  bd sync
  ```

---

## FINAL VERIFICATION CHECKLIST

### Code Quality
- [ ] No syntax errors
- [ ] No import errors
- [ ] All tests pass (65+ tests)
- [ ] No regressions in existing functionality
- [ ] Code follows project conventions (structlog, time.monotonic, etc.)

### Documentation
- [ ] AGENTS.md updated
- [ ] Code docstrings complete
- [ ] Examples provided
- [ ] Configuration documented

### Git
- [ ] Changes committed with clear messages
- [ ] Beads updated and synced
- [ ] No uncommitted changes

### Testing
- [ ] Unit tests for TokenBucket
- [ ] Integration tests for HTTPProvider
- [ ] Concurrent access tests
- [ ] Edge case tests

---

## SUCCESS CRITERIA

### Functional
- ✅ TokenBucket correctly refills tokens
- ✅ Sync path respects rate limit
- ✅ Async path respects rate limit
- ✅ RateLimitError raised when limit exceeded
- ✅ Concurrent requests handled correctly

### Integration
- ✅ HTTPProvider uses rate limiter
- ✅ Circuit breaker + rate limiter work together
- ✅ No deadlocks or race conditions
- ✅ Logging shows rate limit events

### Testing
- ✅ Unit tests for TokenBucket (sync, async, concurrent)
- ✅ Integration tests for HTTPProvider
- ✅ All existing tests still pass

### Documentation
- ✅ AGENTS.md updated
- ✅ Code docstrings complete
- ✅ Design decisions documented

---

## ESTIMATED TIME BREAKDOWN

| Task | Estimated Time |
|------|-----------------|
| Task 1: Create rate_limiter.py | 1 hour |
| Task 2: Integrate into HTTPProvider | 30 minutes |
| Task 3: Unit tests | 1.5 hours |
| Task 4: Integration tests | 1 hour |
| Task 5: Run full test suite | 30 minutes |
| Task 6: Update documentation | 30 minutes |
| Task 7: Create beads | 15 minutes |
| **Total** | **5.5 hours** |

---

**Document Version**: 1.0  
**Status**: ✅ Ready for Implementation  
**Next Step**: Begin Task 1 (Create rate_limiter.py)
