# Phase 2: Resilience - Code Snippets & Templates

**Quick Reference**: Copy-paste ready code for implementation

---

## 1. CircuitBreaker Class (circuit_breaker.py)

### 1.1 Imports & Enums

```python
"""
Circuit Breaker Pattern Implementation

Provides resilience for HTTP-based providers by preventing cascading failures.
States: CLOSED (normal) → OPEN (too many failures) → HALF_OPEN (testing) → CLOSED
"""

from enum import Enum
from dataclasses import dataclass
from time import time
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 2
```

### 1.2 Exception Classes

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

### 1.3 CircuitBreaker Class

```python
class CircuitBreaker:
    """
    Lightweight circuit breaker for HTTP providers.
    
    Prevents cascading failures by:
    1. Tracking failure count
    2. Opening circuit after threshold
    3. Testing recovery after timeout
    4. Closing circuit after successes
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker."""
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
    
    def is_open(self) -> bool:
        """Check if circuit is open and handle timeout."""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self._timeout_elapsed():
                self._transition_to(CircuitState.HALF_OPEN)
                return False
            return True
        return False
    
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self.state == CircuitState.HALF_OPEN
    
    def record_success(self):
        """Record successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self, exception: Exception):
        """Record failed request."""
        self.last_failure_time = time()
        self.failure_count += 1
        
        logger.warning(
            "circuit_breaker_failure_recorded",
            failure_count=self.failure_count,
            threshold=self.config.failure_threshold,
            exception_type=type(exception).__name__,
        )
        
        if self.failure_count >= self.config.failure_threshold:
            self._transition_to(CircuitState.OPEN)
    
    def _timeout_elapsed(self) -> bool:
        """Check if recovery timeout has elapsed."""
        if self.last_failure_time is None:
            return False
        elapsed = time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout
    
    def _transition_to(self, new_state: CircuitState):
        """Transition to new state with logging."""
        old_state = self.state
        self.state = new_state
        
        # Reset counters on state change
        if new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.success_count = 0
        
        logger.info(
            "circuit_breaker_state_transition",
            old_state=old_state.value,
            new_state=new_state.value,
            failure_count=self.failure_count,
            success_count=self.success_count,
        )
    
    def get_state(self) -> str:
        """Get current state as string."""
        return self.state.value
```

---

## 2. HTTPProvider Modifications (base.py)

### 2.1 Update __init__

```python
def __init__(self):
    """Initialize HTTP provider with session and circuit breaker."""
    super().__init__()
    self.session = None  # Initialized on first use
    self.async_client = None  # NEW: Initialized on first async use
    self.headers = self._setup_headers()
    self.circuit_breaker = self._create_circuit_breaker()  # NEW
```

### 2.2 Add Circuit Breaker Configuration

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

### 2.3 Add Helper Method

```python
def _create_circuit_breaker(self):
    """Create circuit breaker with configuration."""
    from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
    
    config = CircuitBreakerConfig(
        failure_threshold=self.config.get("cb_failure_threshold", 5),
        recovery_timeout=self.config.get("cb_recovery_timeout", 60),
        success_threshold=self.config.get("cb_success_threshold", 2),
    )
    return CircuitBreaker(config)
```

### 2.4 Implement Async Client

```python
async def _get_async_client(self):
    """Get or create async HTTP client with connection pooling."""
    if self.async_client is None:
        import httpx
        
        timeout = httpx.Timeout(self.config.get("timeout", 60))
        limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
        )
        
        self.async_client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
        )
        
        logger.debug(
            "async_client_created",
            timeout=self.config.get("timeout", 60),
            max_connections=10,
        )
    
    return self.async_client
```

### 2.5 Update __aexit__

```python
async def __aexit__(self, exc_type, exc_val, exc_tb):
    """Async context manager exit with cleanup."""
    if self.async_client is not None:
        await self.async_client.aclose()
        self.async_client = None
        logger.debug("async_client_closed")
```

### 2.6 Wrap _make_request()

```python
def _make_request(
    self, method: str, url: str, json_data: Optional[Dict] = None, **kwargs
) -> Dict[str, Any]:
    """
    Make HTTP request with circuit breaker protection.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        json_data: JSON payload for POST requests
        **kwargs: Additional request parameters
    
    Returns:
        Response data as dictionary
    
    Raises:
        CircuitBreakerOpenError: If circuit breaker is open
        requests.RequestException: If request fails
    """
    from .circuit_breaker import CircuitBreakerOpenError
    
    # Check circuit breaker state
    if self.circuit_breaker.is_open():
        logger.warning(
            "circuit_breaker_open",
            provider=self.__class__.__name__,
            url=url,
        )
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
        
        logger.error(
            "http_request_failed",
            method=method,
            url=url,
            error=str(e),
            error_type=type(e).__name__,
            circuit_breaker_state=self.circuit_breaker.get_state(),
        )
        raise
```

### 2.7 Wrap _make_request_async()

```python
async def _make_request_async(
    self, method: str, url: str, json_data: Optional[Dict] = None, **kwargs
) -> Dict[str, Any]:
    """
    Make async HTTP request with circuit breaker protection.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        json_data: JSON payload for POST requests
        **kwargs: Additional request parameters
    
    Returns:
        Response data as dictionary
    
    Raises:
        CircuitBreakerOpenError: If circuit breaker is open
        httpx.RequestError: If request fails
    """
    from .circuit_breaker import CircuitBreakerOpenError
    
    # Check circuit breaker state
    if self.circuit_breaker.is_open():
        logger.warning(
            "circuit_breaker_open_async",
            provider=self.__class__.__name__,
            url=url,
        )
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
        
        logger.error(
            "async_http_request_failed",
            method=method,
            url=url,
            error=str(e),
            error_type=type(e).__name__,
            circuit_breaker_state=self.circuit_breaker.get_state(),
        )
        raise
```

---

## 3. Unit Tests (test_circuit_breaker.py)

### 3.1 Test Imports

```python
import pytest
from time import sleep
from docflow.models.providers.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpenError,
)
```

### 3.2 Test State Transitions

```python
class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state machine."""
    
    def test_circuit_breaker_starts_closed(self):
        """Circuit breaker should start in CLOSED state."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.is_open() is False
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Circuit breaker should open after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)
        
        # Record failures
        for i in range(3):
            cb.record_failure(Exception(f"failure {i}"))
        
        assert cb.state == CircuitState.OPEN
        assert cb.is_open() is True
        assert cb.failure_count == 3
    
    def test_circuit_breaker_half_opens_after_timeout(self):
        """Circuit breaker should transition to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=1,  # 1 second
        )
        cb = CircuitBreaker(config)
        
        # Open the circuit
        cb.record_failure(Exception("failure"))
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        sleep(1.1)
        
        # Check if half-open
        assert cb.is_open() is False
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_circuit_breaker_closes_after_successes(self):
        """Circuit breaker should close after success threshold in HALF_OPEN."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,
        )
        cb = CircuitBreaker(config)
        
        # Open the circuit
        cb.record_failure(Exception("failure"))
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        sleep(0.2)
        assert cb.state == CircuitState.HALF_OPEN
        
        # Record successes
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
```

### 3.3 Test Failure Counting

```python
class TestCircuitBreakerFailureCounting:
    """Test failure counting logic."""
    
    def test_failure_count_increments(self):
        """Failure count should increment on each failure."""
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker(config)
        
        for i in range(3):
            cb.record_failure(Exception(f"failure {i}"))
            assert cb.failure_count == i + 1
    
    def test_failure_count_resets_on_success(self):
        """Failure count should reset on success in CLOSED state."""
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker(config)
        
        # Record some failures
        cb.record_failure(Exception("failure"))
        cb.record_failure(Exception("failure"))
        assert cb.failure_count == 2
        
        # Record success
        cb.record_success()
        assert cb.failure_count == 0
```

---

## 4. Integration Tests (test_http_provider_circuit_breaker.py)

### 4.1 Test HTTPProvider Integration

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from docflow.models.providers.base import HTTPProvider
from docflow.models.providers.circuit_breaker import (
    CircuitBreakerOpenError,
    CircuitState,
)


class ConcreteHTTPProvider(HTTPProvider):
    """Concrete implementation for testing."""
    
    def _load_config(self):
        return HTTPProvider.DEFAULT_CONFIG.copy()
    
    def _setup_headers(self):
        return {"Content-Type": "application/json"}
    
    @classmethod
    def is_available(cls):
        return True
    
    def generate(self, prompt, images=None, temperature=None, max_tokens=None, **kwargs):
        return "test response"
    
    def extract_information(self, text, image_path=None):
        return {"success": True}
    
    async def extract_information_async(self, text, image_path=None):
        return {"success": True}


class TestHTTPProviderCircuitBreaker:
    """Test HTTPProvider circuit breaker integration."""
    
    def test_http_provider_creates_circuit_breaker(self):
        """HTTPProvider should create circuit breaker on init."""
        provider = ConcreteHTTPProvider()
        
        assert provider.circuit_breaker is not None
        assert provider.circuit_breaker.state == CircuitState.CLOSED
    
    def test_http_provider_rejects_request_when_cb_open(self):
        """HTTPProvider should reject requests when CB is open."""
        provider = ConcreteHTTPProvider()
        provider.circuit_breaker.state = CircuitState.OPEN
        provider.circuit_breaker.last_failure_time = 0  # Prevent auto-recovery
        
        with pytest.raises(CircuitBreakerOpenError):
            provider._make_request("GET", "http://example.com")
    
    def test_http_provider_records_success(self):
        """HTTPProvider should record success on successful request."""
        provider = ConcreteHTTPProvider()
        
        with patch.object(provider, '_get_session') as mock_session:
            mock_response = Mock()
            mock_response.json.return_value = {"success": True}
            mock_session.return_value.request.return_value = mock_response
            
            result = provider._make_request("GET", "http://example.com")
            
            assert result == {"success": True}
            assert provider.circuit_breaker.failure_count == 0
    
    def test_http_provider_records_failure(self):
        """HTTPProvider should record failure on failed request."""
        provider = ConcreteHTTPProvider()
        
        with patch.object(provider, '_get_session') as mock_session:
            mock_session.return_value.request.side_effect = Exception("Connection error")
            
            with pytest.raises(Exception):
                provider._make_request("GET", "http://example.com")
            
            assert provider.circuit_breaker.failure_count == 1
```

---

## 5. Configuration Example

```python
# In your provider subclass
class MyHTTPProvider(HTTPProvider):
    def _load_config(self):
        config = super()._load_config()
        config.update({
            "timeout": 30,
            "max_retries": 5,
            "retry_backoff": 2.0,
            # Circuit Breaker
            "cb_enabled": True,
            "cb_failure_threshold": 5,
            "cb_recovery_timeout": 60,
            "cb_success_threshold": 2,
        })
        return config
```

---

## 6. Logging Examples

### 6.1 State Transitions

```
circuit_breaker_state_transition: old_state=CLOSED new_state=OPEN failure_count=5 success_count=0
circuit_breaker_state_transition: old_state=OPEN new_state=HALF_OPEN failure_count=5 success_count=0
circuit_breaker_state_transition: old_state=HALF_OPEN new_state=CLOSED failure_count=0 success_count=2
```

### 6.2 Request Handling

```
circuit_breaker_open: provider=OpenAIProvider url=https://api.openai.com/v1/chat/completions
http_request_failed: method=POST url=https://api.openai.com/v1/chat/completions error=ConnectionError circuit_breaker_state=CLOSED
circuit_breaker_failure_recorded: failure_count=1 threshold=5 exception_type=ConnectionError
```

---

## 7. Quick Checklist

### Before Implementation
- [ ] Read circuit-breaker-analysis.md
- [ ] Review HTTPProvider architecture
- [ ] Check httpx documentation
- [ ] Verify structlog is available

### During Implementation
- [ ] Create circuit_breaker.py with all classes
- [ ] Fix async client in base.py
- [ ] Integrate CB into _make_request()
- [ ] Integrate CB into _make_request_async()
- [ ] Add exception classes
- [ ] Write unit tests
- [ ] Write integration tests

### After Implementation
- [ ] All tests pass
- [ ] No LSP errors
- [ ] Code coverage > 85%
- [ ] Logging shows state transitions
- [ ] Documentation updated

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-14  
**Author**: Sisyphus-Junior
