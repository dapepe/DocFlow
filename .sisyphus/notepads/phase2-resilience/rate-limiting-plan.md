# Phase 2: Resilience (Rate Limiting) - Implementation Plan

**Date**: 2026-02-14  
**Status**: Analysis Complete  
**Scope**: Design and planning for rate limiting implementation

---

## EXECUTIVE SUMMARY

Rate limiting is the second resilience pattern for Phase 2 (after Circuit Breaker). The goal is to prevent overwhelming external APIs by controlling request throughput using a **Token Bucket** algorithm.

### Key Findings
1. **No external rate limiting library** in `requirements.txt` (good - aligns with Circuit Breaker approach)
2. **HTTPProvider** is the injection point for rate limiting (lines 174-332 in `base.py`)
3. **Circuit Breaker pattern** already established (thread-safe, time-based state management)
4. **Async-first architecture** requires thread-safe AND async-safe implementation
5. **Existing patterns**: `structlog` for logging, `time.monotonic()` for timing

---

## ANALYSIS

### 1. Current HTTPProvider Architecture

**Location**: `docflow/models/providers/base.py:174-332`

**Current Flow**:
```
HTTPProvider.__init__()
  ├── self.session = None (lazy init)
  ├── self.async_client = None (lazy init)
  ├── self.headers = _setup_headers()
  └── self.circuit_breaker = CircuitBreaker()

_make_request() [SYNC]
  ├── circuit_breaker.can_execute()
  ├── session.request()
  └── circuit_breaker.record_success/failure()

_make_request_async() [ASYNC]
  ├── circuit_breaker.can_execute()
  ├── client.request()
  └── circuit_breaker.record_success/failure()
```

**Injection Points for Rate Limiting**:
- **Before** `circuit_breaker.can_execute()` → Check rate limit
- **After** successful request → Update token bucket
- **On failure** → Don't consume tokens (let circuit breaker handle)

### 2. Token Bucket Algorithm

**Why Token Bucket?**
- Simple, efficient, no external dependencies
- Handles burst traffic (tokens accumulate)
- Thread-safe with proper locking
- Async-compatible with asyncio locks

**Algorithm**:
```
tokens_available = min(capacity, tokens + (time_elapsed * refill_rate))
if tokens_available >= cost:
    tokens_available -= cost
    return True (allow request)
else:
    return False (rate limited)
```

**Parameters**:
- `capacity`: Max tokens (e.g., 100)
- `refill_rate`: Tokens per second (e.g., 10 = 10 requests/sec)
- `cost`: Tokens per request (default 1)

### 3. Thread-Safety & Async-Safety Requirements

**Current State**:
- Circuit Breaker uses `time.monotonic()` (thread-safe)
- No locks in Circuit Breaker (state transitions are atomic)
- HTTPProvider has both sync (`_make_request`) and async (`_make_request_async`) paths

**Rate Limiter Requirements**:
- **Sync path**: Use `threading.Lock` for token bucket updates
- **Async path**: Use `asyncio.Lock` for token bucket updates
- **Shared state**: Both paths must see same token count

**Solution**: Dual-lock approach
```python
class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self._tokens = capacity
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._last_refill = time.monotonic()
        
        # Sync lock for _make_request()
        self._sync_lock = threading.Lock()
        
        # Async lock for _make_request_async()
        self._async_lock = None  # Lazy init in async context
    
    def try_acquire(self, cost=1) -> bool:
        """Sync version - uses threading.Lock"""
        with self._sync_lock:
            self._refill()
            if self._tokens >= cost:
                self._tokens -= cost
                return True
            return False
    
    async def try_acquire_async(self, cost=1) -> bool:
        """Async version - uses asyncio.Lock"""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        
        async with self._async_lock:
            self._refill()
            if self._tokens >= cost:
                self._tokens -= cost
                return True
            return False
```

### 4. Configuration Strategy

**Where to store rate limit config?**

Option A: `HTTPProvider.DEFAULT_CONFIG` (preferred)
```python
DEFAULT_CONFIG = {
    "timeout": 60,
    "max_retries": 3,
    "retry_backoff": 1.0,
    "rate_limit_capacity": 100,      # NEW
    "rate_limit_refill_rate": 10.0,  # NEW (tokens/sec)
}
```

Option B: Environment variables (`.env`)
```
RATE_LIMIT_CAPACITY=100
RATE_LIMIT_REFILL_RATE=10.0
```

**Recommendation**: Use Option A (DEFAULT_CONFIG) with env var override capability
- Sensible defaults for all providers
- Per-provider customization via subclass override
- No new env vars needed initially

### 5. Error Handling Strategy

**When rate limited, what happens?**

Current approach (Circuit Breaker):
- Fails fast with `CircuitBreakerOpenError`
- Caller decides retry strategy

Proposed approach (Rate Limiter):
- **Option 1**: Fail fast with `RateLimitError` (like Circuit Breaker)
- **Option 2**: Block/wait until tokens available (not recommended - could deadlock)
- **Option 3**: Exponential backoff retry (complex, let caller handle)

**Recommendation**: Option 1 (fail fast)
- Consistent with Circuit Breaker pattern
- Caller can implement retry logic
- Prevents cascading delays

**New Exception**:
```python
class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after:.2f}s")
```

### 6. Integration Points

**Files to Create**:
1. `docflow/rate_limiter.py` - TokenBucket implementation

**Files to Modify**:
1. `docflow/models/providers/base.py` - HTTPProvider integration
2. `docflow/models/providers/__init__.py` - Export RateLimitError (if needed)

**No changes needed**:
- `circuit_breaker.py` - Separate concern
- `processor.py` - Handled at provider level
- `api.py` - Handled at provider level
- Tests - Will add new tests for rate limiter

### 7. Testing Strategy

**Unit Tests** (`tests/test_rate_limiter.py`):
- Token bucket refill calculation
- Sync acquire (threading.Lock)
- Async acquire (asyncio.Lock)
- Rate limit exceeded behavior
- Concurrent requests (stress test)

**Integration Tests** (`tests/test_http_provider_rate_limit.py`):
- HTTPProvider with rate limiter enabled
- Sync and async paths
- Circuit breaker + rate limiter interaction

---

## IMPLEMENTATION ROADMAP

### Phase 2.2: Rate Limiting (This Phase)

**Task 1**: Create `docflow/rate_limiter.py`
- TokenBucket class with dual-lock support
- Sync `try_acquire()` method
- Async `try_acquire_async()` method
- RateLimitError exception
- Comprehensive docstrings

**Task 2**: Integrate into HTTPProvider
- Add rate limiter instance to `__init__`
- Call `rate_limiter.try_acquire()` in `_make_request()`
- Call `rate_limiter.try_acquire_async()` in `_make_request_async()`
- Handle RateLimitError (log and re-raise)
- Add config parameters to DEFAULT_CONFIG

**Task 3**: Add unit tests
- `tests/test_rate_limiter.py` - TokenBucket behavior
- Test sync and async paths
- Test concurrent access
- Test refill calculation

**Task 4**: Add integration tests
- `tests/test_http_provider_rate_limit.py`
- Mock API calls with rate limiting
- Verify circuit breaker + rate limiter interaction

**Task 5**: Documentation
- Update AGENTS.md with rate limiting notes
- Add docstrings to rate_limiter.py
- Update README if needed

---

## DESIGN DECISIONS

### 1. Token Bucket vs Leaky Bucket vs Sliding Window

| Algorithm | Pros | Cons | Choice |
|-----------|------|------|--------|
| **Token Bucket** | Handles bursts, simple | Requires refill calculation | ✅ CHOSEN |
| **Leaky Bucket** | Smooth rate | No burst handling | ❌ |
| **Sliding Window** | Accurate | Complex, memory overhead | ❌ |

### 2. Dual-Lock vs Single Lock

| Approach | Pros | Cons | Choice |
|----------|------|------|--------|
| **Dual-Lock** (threading + asyncio) | Correct for both paths | Slightly more code | ✅ CHOSEN |
| **Single Lock** | Simpler | Doesn't work (threading.Lock blocks async) | ❌ |
| **No Lock** | Fastest | Race conditions | ❌ |

### 3. Fail-Fast vs Wait

| Approach | Pros | Cons | Choice |
|----------|------|------|--------|
| **Fail-Fast** | Consistent with Circuit Breaker | Caller must retry | ✅ CHOSEN |
| **Wait** | Transparent to caller | Can deadlock, unpredictable latency | ❌ |

### 4. Config Location

| Location | Pros | Cons | Choice |
|----------|------|------|--------|
| **DEFAULT_CONFIG** | Centralized, per-provider override | Requires code change | ✅ CHOSEN |
| **Env vars** | Runtime config | More env vars | ❌ (secondary) |
| **config/rules.yaml** | Persistent config | Overkill for this | ❌ |

---

## PSEUDO-CODE

### rate_limiter.py

```python
import asyncio
import threading
import time
from typing import Optional

class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after:.2f}s")

class TokenBucket:
    """Token bucket rate limiter with sync and async support."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Max tokens (e.g., 100)
            refill_rate: Tokens per second (e.g., 10)
        """
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._sync_lock = threading.Lock()
        self._async_lock: Optional[asyncio.Lock] = None
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._refill_rate
        )
        self._last_refill = now
    
    def try_acquire(self, cost: float = 1.0) -> bool:
        """Try to acquire tokens (sync version)."""
        with self._sync_lock:
            self._refill()
            if self._tokens >= cost:
                self._tokens -= cost
                return True
            return False
    
    async def try_acquire_async(self, cost: float = 1.0) -> bool:
        """Try to acquire tokens (async version)."""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        
        async with self._async_lock:
            self._refill()
            if self._tokens >= cost:
                self._tokens -= cost
                return True
            return False
    
    def get_retry_after(self, cost: float = 1.0) -> float:
        """Calculate seconds until tokens available."""
        with self._sync_lock:
            self._refill()
            if self._tokens >= cost:
                return 0.0
            deficit = cost - self._tokens
            return deficit / self._refill_rate
```

### HTTPProvider integration

```python
class HTTPProvider(BaseProvider):
    DEFAULT_CONFIG = {
        "timeout": 60,
        "max_retries": 3,
        "retry_backoff": 1.0,
        "rate_limit_capacity": 100,
        "rate_limit_refill_rate": 10.0,
    }
    
    def __init__(self):
        super().__init__()
        self.session = None
        self.async_client = None
        self.headers = self._setup_headers()
        self.circuit_breaker = CircuitBreaker()
        
        # NEW: Rate limiter
        from docflow.rate_limiter import TokenBucket
        self.rate_limiter = TokenBucket(
            capacity=self.config.get("rate_limit_capacity", 100),
            refill_rate=self.config.get("rate_limit_refill_rate", 10.0),
        )
    
    def _make_request(self, method: str, url: str, ...) -> Dict[str, Any]:
        # NEW: Check rate limit
        if not self.rate_limiter.try_acquire():
            retry_after = self.rate_limiter.get_retry_after()
            logger.warning("rate_limit_exceeded", retry_after=retry_after)
            raise RateLimitError(retry_after)
        
        # Existing: Circuit breaker
        self.circuit_breaker.can_execute()
        
        # Existing: Make request
        ...
    
    async def _make_request_async(self, method: str, url: str, ...) -> Dict[str, Any]:
        # NEW: Check rate limit
        if not await self.rate_limiter.try_acquire_async():
            retry_after = self.rate_limiter.get_retry_after()
            logger.warning("rate_limit_exceeded", retry_after=retry_after)
            raise RateLimitError(retry_after)
        
        # Existing: Circuit breaker
        self.circuit_breaker.can_execute()
        
        # Existing: Make request
        ...
```

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Async lock initialization race** | Multiple asyncio.Lock created | Lazy init in try_acquire_async with check |
| **Token bucket starvation** | One provider starves others | Per-provider rate limiter (current design) |
| **Config not loaded** | Default values used | Sensible defaults in DEFAULT_CONFIG |
| **Interaction with Circuit Breaker** | Confusing error handling | Clear logging, separate exceptions |
| **Performance overhead** | Lock contention | Minimal (only on request path) |

---

## SUCCESS CRITERIA

### Functional
- [ ] TokenBucket correctly refills tokens
- [ ] Sync path respects rate limit
- [ ] Async path respects rate limit
- [ ] RateLimitError raised when limit exceeded
- [ ] Concurrent requests handled correctly

### Integration
- [ ] HTTPProvider uses rate limiter
- [ ] Circuit breaker + rate limiter work together
- [ ] No deadlocks or race conditions
- [ ] Logging shows rate limit events

### Testing
- [ ] Unit tests for TokenBucket (sync, async, concurrent)
- [ ] Integration tests for HTTPProvider
- [ ] All existing tests still pass

### Documentation
- [ ] AGENTS.md updated
- [ ] Code docstrings complete
- [ ] Design decisions documented

---

## NEXT STEPS

1. **Create rate_limiter.py** with TokenBucket implementation
2. **Integrate into HTTPProvider** (base.py)
3. **Write unit tests** (test_rate_limiter.py)
4. **Write integration tests** (test_http_provider_rate_limit.py)
5. **Update documentation** (AGENTS.md)
6. **Run full test suite** to ensure no regressions
7. **Create beads** for Phase 2.2 tasks

---

## APPENDIX: Configuration Examples

### Default (10 requests/sec, burst up to 100)
```python
DEFAULT_CONFIG = {
    "rate_limit_capacity": 100,
    "rate_limit_refill_rate": 10.0,
}
```

### Conservative (1 request/sec, burst up to 10)
```python
DEFAULT_CONFIG = {
    "rate_limit_capacity": 10,
    "rate_limit_refill_rate": 1.0,
}
```

### Aggressive (100 requests/sec, burst up to 1000)
```python
DEFAULT_CONFIG = {
    "rate_limit_capacity": 1000,
    "rate_limit_refill_rate": 100.0,
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

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-14  
**Status**: Ready for Implementation
