# Phase 2: Resilience (Rate Limiting) - Analysis Summary

**Date**: 2026-02-14  
**Analyst**: Sisyphus-Junior  
**Status**: ✅ Analysis Complete

---

## QUICK FINDINGS

### 1. No External Dependencies Needed ✅
- `requirements.txt` has NO rate limiting library (good!)
- Aligns with Circuit Breaker approach (custom implementation)
- Only stdlib needed: `threading`, `asyncio`, `time`

### 2. HTTPProvider is the Injection Point ✅
- **File**: `docflow/models/providers/base.py` (lines 174-332)
- **Methods to intercept**:
  - `_make_request()` - Sync HTTP requests
  - `_make_request_async()` - Async HTTP requests
- **Already has**: Circuit breaker integration (pattern to follow)

### 3. Architecture is Async-First ✅
- Both sync and async paths exist
- Requires **dual-lock approach**:
  - `threading.Lock` for sync path
  - `asyncio.Lock` for async path
- Shared token bucket state between both

### 4. Circuit Breaker Pattern is Established ✅
- **File**: `docflow/circuit_breaker.py` (182 lines)
- **Pattern**: Time-based state machine, thread-safe
- **Logging**: Uses `structlog` (consistent)
- **Timing**: Uses `time.monotonic()` (correct)
- **Rate limiter should follow same pattern**

### 5. Configuration Strategy ✅
- Use `HTTPProvider.DEFAULT_CONFIG` (existing pattern)
- Add two new keys:
  - `rate_limit_capacity`: Max tokens (default: 100)
  - `rate_limit_refill_rate`: Tokens/sec (default: 10.0)
- Per-provider override via subclass

---

## IMPLEMENTATION SCOPE

### Files to Create
1. **`docflow/rate_limiter.py`** (NEW)
   - `TokenBucket` class
   - `RateLimitError` exception
   - ~150 lines of code

### Files to Modify
1. **`docflow/models/providers/base.py`**
   - Add rate limiter to `HTTPProvider.__init__`
   - Call `rate_limiter.try_acquire()` in `_make_request()`
   - Call `rate_limiter.try_acquire_async()` in `_make_request_async()`
   - Add config keys to `DEFAULT_CONFIG`
   - ~30 lines of changes

### Files to Create (Tests)
1. **`tests/test_rate_limiter.py`** (NEW)
   - Unit tests for TokenBucket
   - Sync, async, concurrent scenarios
   - ~200 lines

2. **`tests/test_http_provider_rate_limit.py`** (NEW)
   - Integration tests
   - HTTPProvider + rate limiter
   - ~150 lines

### Files to Update (Documentation)
1. **`docflow/models/providers/AGENTS.md`**
   - Add rate limiting section
   - Document configuration

---

## TOKEN BUCKET ALGORITHM

### Core Logic
```
tokens_available = min(capacity, tokens + (time_elapsed * refill_rate))
if tokens_available >= cost:
    tokens_available -= cost
    return True (allow request)
else:
    return False (rate limited)
```

### Example: 10 requests/sec with burst to 100
```
capacity = 100 tokens
refill_rate = 10 tokens/sec

Scenario 1: Normal load
  - Request 1: 100 tokens available → acquire 1 → 99 left
  - Wait 0.1s: 100 tokens available (refilled) → acquire 1 → 99 left
  - Result: 10 requests/sec sustained

Scenario 2: Burst
  - Requests 1-100: All succeed (use all 100 tokens)
  - Request 101: 0 tokens available → RATE LIMITED
  - Wait 10s: 100 tokens refilled → Request 101 succeeds
  - Result: Can burst up to 100 requests, then throttled to 10/sec
```

---

## DUAL-LOCK DESIGN

### Why Dual-Lock?
- `threading.Lock` blocks the entire thread (OK for sync)
- `asyncio.Lock` is async-aware (required for async)
- Can't use `threading.Lock` in async context (deadlock)
- Can't use `asyncio.Lock` in sync context (not awaitable)

### Implementation
```python
class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self._sync_lock = threading.Lock()      # For _make_request()
        self._async_lock = None                 # Lazy init for _make_request_async()
    
    def try_acquire(self, cost=1):
        with self._sync_lock:
            # Update tokens and check
    
    async def try_acquire_async(self, cost=1):
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        async with self._async_lock:
            # Update tokens and check
```

### Shared State
- Both locks protect the same `_tokens` variable
- Refill calculation is identical in both paths
- No race conditions (each path has its own lock)

---

## ERROR HANDLING

### New Exception: RateLimitError
```python
class RateLimitError(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after:.2f}s")
```

### Fail-Fast Strategy
- Raise `RateLimitError` immediately when rate limited
- Caller decides retry strategy
- Consistent with Circuit Breaker pattern
- Prevents cascading delays

### Logging
- Use `structlog` (consistent with codebase)
- Log when rate limit exceeded
- Include `retry_after` value

---

## INTEGRATION WITH CIRCUIT BREAKER

### Order of Checks
```
_make_request():
  1. Check rate limit (NEW)
     ├─ If limited: raise RateLimitError
     └─ If OK: continue
  
  2. Check circuit breaker (EXISTING)
     ├─ If open: raise CircuitBreakerOpenError
     └─ If OK: continue
  
  3. Make HTTP request (EXISTING)
     ├─ On success: record_success()
     └─ On failure: record_failure()
```

### Why This Order?
- Rate limit is cheaper to check (no state machine)
- Circuit breaker is more critical (prevents cascading failures)
- Both are independent concerns

---

## CONFIGURATION EXAMPLES

### Default (10 requests/sec, burst to 100)
```python
DEFAULT_CONFIG = {
    "timeout": 60,
    "max_retries": 3,
    "retry_backoff": 1.0,
    "rate_limit_capacity": 100,
    "rate_limit_refill_rate": 10.0,
}
```

### Per-Provider Override
```python
class OpenAIProvider(HTTPProvider):
    DEFAULT_CONFIG = {
        **HTTPProvider.DEFAULT_CONFIG,
        "rate_limit_capacity": 60,      # OpenAI: 60 RPM
        "rate_limit_refill_rate": 1.0,  # 1 request/sec
    }
```

### Environment Variable Override (Future)
```python
# In HTTPProvider.__init__:
capacity = int(os.getenv("RATE_LIMIT_CAPACITY", 
                         self.config.get("rate_limit_capacity", 100)))
refill_rate = float(os.getenv("RATE_LIMIT_REFILL_RATE",
                              self.config.get("rate_limit_refill_rate", 10.0)))
```

---

## TESTING STRATEGY

### Unit Tests (test_rate_limiter.py)
- [ ] Token refill calculation
- [ ] Sync acquire (threading.Lock)
- [ ] Async acquire (asyncio.Lock)
- [ ] Rate limit exceeded
- [ ] Concurrent requests (stress test)
- [ ] get_retry_after() calculation

### Integration Tests (test_http_provider_rate_limit.py)
- [ ] HTTPProvider with rate limiter
- [ ] Sync path respects limit
- [ ] Async path respects limit
- [ ] Circuit breaker + rate limiter interaction
- [ ] Error handling (RateLimitError)

### Existing Tests
- All 65 existing tests should still pass
- No changes to test files needed

---

## RISKS & MITIGATIONS

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Async lock race condition | Medium | Lazy init with None check in try_acquire_async |
| Token bucket starvation | Low | Per-provider rate limiter (current design) |
| Config not loaded | Low | Sensible defaults in DEFAULT_CONFIG |
| Lock contention | Low | Minimal (only on request path) |
| Interaction with Circuit Breaker | Medium | Clear logging, separate exceptions |

---

## DESIGN DECISIONS

### 1. Token Bucket Algorithm ✅
- **Why**: Handles bursts, simple, no external deps
- **Alternative**: Leaky bucket (no burst), Sliding window (complex)

### 2. Dual-Lock Approach ✅
- **Why**: Correct for both sync and async paths
- **Alternative**: Single lock (doesn't work), No lock (race conditions)

### 3. Fail-Fast Strategy ✅
- **Why**: Consistent with Circuit Breaker, caller controls retry
- **Alternative**: Wait (can deadlock), Exponential backoff (complex)

### 4. Config in DEFAULT_CONFIG ✅
- **Why**: Centralized, per-provider override, no new env vars
- **Alternative**: Env vars (more config), rules.yaml (overkill)

---

## NEXT STEPS (IMPLEMENTATION)

### Phase 2.2: Rate Limiting Tasks

**Task 1**: Create `docflow/rate_limiter.py`
- TokenBucket class with dual-lock support
- RateLimitError exception
- Comprehensive docstrings

**Task 2**: Integrate into HTTPProvider
- Add rate limiter to `__init__`
- Call in `_make_request()` and `_make_request_async()`
- Add config parameters

**Task 3**: Unit tests
- `tests/test_rate_limiter.py`
- Sync, async, concurrent scenarios

**Task 4**: Integration tests
- `tests/test_http_provider_rate_limit.py`
- HTTPProvider + rate limiter

**Task 5**: Documentation
- Update AGENTS.md
- Add docstrings

---

## APPENDIX: Code Snippets

### TokenBucket._refill() Logic
```python
def _refill(self) -> None:
    """Refill tokens based on elapsed time."""
    now = time.monotonic()
    elapsed = now - self._last_refill
    self._tokens = min(
        self._capacity,
        self._tokens + elapsed * self._refill_rate
    )
    self._last_refill = now
```

### HTTPProvider Integration
```python
def _make_request(self, method: str, url: str, ...) -> Dict[str, Any]:
    # NEW: Check rate limit
    if not self.rate_limiter.try_acquire():
        retry_after = self.rate_limiter.get_retry_after()
        logger.warning("rate_limit_exceeded", retry_after=retry_after)
        raise RateLimitError(retry_after)
    
    # EXISTING: Circuit breaker + request
    self.circuit_breaker.can_execute()
    # ... rest of method
```

---

**Document Version**: 1.0  
**Status**: ✅ Ready for Implementation  
**Estimated Effort**: 4-6 hours (including tests)
