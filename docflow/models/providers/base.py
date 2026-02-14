"""
Unified Provider Architecture

Provides base classes and interfaces for all LLM providers.
This architecture makes it easy to add new backends (vLLM, TGI, etc.)
by implementing the BaseProvider interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import structlog

from docflow.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = structlog.get_logger(__name__)


class ProviderCapabilities:
    """Standard capability flags for all providers."""

    def __init__(self):
        self.vision = False
        self.multilingual = False
        self.streaming = False
        self.structured_output = False
        self.local = False
        self.gpu_acceleration = False
        self.long_context = False
        self.reasoning = False
        self.ocr = False
        self.fast = False
        self.document_specialized = False


class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.

    All provider implementations (Ollama, llama.cpp, Anthropic, Google, etc.)
    must inherit from this class and implement all abstract methods.

    This provides a unified interface for:
    - Text generation
    - Vision/multimodal processing
    - Structured JSON output
    - Model availability checking
    - Capability reporting
    """

    # Override in subclasses
    description: str = "Base Provider"
    requires_env_vars: List[str] = []

    def __init__(self):
        """Initialize the provider."""
        self.capabilities = ProviderCapabilities()
        self.config = self._load_config()
        logger.info("provider_initialized", provider_class=self.__class__.__name__)

    @abstractmethod
    def _load_config(self) -> Dict[str, Any]:
        """Load provider-specific configuration."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Generate text from the model.

        Args:
            prompt: The text prompt
            images: Optional list of base64-encoded images for multimodal models
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def extract_information(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured information from text and/or image.

        This is the main interface method for document processing.

        Args:
            text: Extracted text content from document
            image_path: Optional path to image for vision analysis

        Returns:
            Dictionary with extraction results including:
            - raw_analysis: The parsed structured data
            - success: Boolean indicating success/failure
            - model_name: Name of the model used
            - provider: Provider identifier
            - validation_passed: Whether schema validation passed
            - validation_errors: List of validation errors if any
        """
        pass

    @abstractmethod
    async def extract_information_async(
        self, text: str, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Async version of extract_information.

        Args:
            text: Extracted text content from document
            image_path: Optional path to image for vision analysis

        Returns:
            Dictionary with extraction results (same structure as sync version)
        """
        pass

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """
        Check if the provider is available in the current environment.

        Returns:
            True if the provider can be used, False otherwise
        """
        pass

    def get_capabilities(self) -> Dict[str, bool]:
        """
        Get provider capabilities as a dictionary.

        Returns:
            Dictionary of capability flags
        """
        return {
            "vision": self.capabilities.vision,
            "multilingual": self.capabilities.multilingual,
            "streaming": self.capabilities.streaming,
            "structured_output": self.capabilities.structured_output,
            "local": self.capabilities.local,
            "gpu_acceleration": self.capabilities.gpu_acceleration,
            "long_context": self.capabilities.long_context,
            "reasoning": self.capabilities.reasoning,
            "ocr": self.capabilities.ocr,
            "fast": self.capabilities.fast,
            "document_specialized": self.capabilities.document_specialized,
        }

    def supports_capability(self, capability: str) -> bool:
        """
        Check if provider supports a specific capability.

        Args:
            capability: Name of capability to check

        Returns:
            True if capability is supported
        """
        return getattr(self.capabilities, capability, False)


class HTTPProvider(BaseProvider):
    """
    Base class for HTTP API-based providers.

    Provides common functionality for providers that use HTTP APIs:
    - Connection pooling
    - Retry logic
    - Authentication
    - Rate limiting

    Examples: Anthropic, Google, OpenAI, OpenRouter
    """

    DEFAULT_CONFIG = {
        "timeout": 60,
        "max_retries": 3,
        "retry_backoff": 1.0,
    }

    def __init__(self):
        """Initialize HTTP provider with session management."""
        super().__init__()
        self.session = None  # Initialized on first use
        self.async_client = None  # Initialized on first async use
        self.headers = self._setup_headers()
        self.circuit_breaker = CircuitBreaker()

    @abstractmethod
    def _setup_headers(self) -> Dict[str, str]:
        """Setup HTTP request headers (authentication, content-type, etc.)."""
        pass

    def _get_session(self):
        """Get or create HTTP session with connection pooling."""
        if self.session is None:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util import Retry

            self.session = requests.Session()

            retry_strategy = Retry(
                total=self.config.get("max_retries", 3),
                backoff_factor=self.config.get("retry_backoff", 1.0),
                status_forcelist=[429, 500, 502, 503, 504],
            )

            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

            logger.debug(
                "http_session_created",
                max_retries=self.config.get("max_retries", 3),
                retry_backoff=self.config.get("retry_backoff", 1.0),
            )

        return self.session

    async def _get_async_client(self):
        """Get or create async HTTP client with connection pooling."""
        if self.async_client is None or self.async_client.is_closed():
            import httpx

            timeout = httpx.Timeout(self.config.get("timeout", 60))
            limits = httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
            )

            self.async_client = httpx.AsyncClient(timeout=timeout, limits=limits)

            logger.debug(
                "async_http_client_created",
                timeout=self.config.get("timeout", 60),
                max_connections=10,
            )

        return self.async_client

    async def _make_request_async(
        self, method: str, url: str, json_data: Optional[Dict] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Make async HTTP request with error handling and circuit breaker protection.
        """
        # Check if circuit breaker allows execution
        self.circuit_breaker.can_execute()

        client = await self._get_async_client()
        try:
            response = await client.request(
                method=method, url=url, json=json_data, **kwargs
            )
            response.raise_for_status()
            self.circuit_breaker.record_success()
            return response.json()
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(
                "async_http_request_failed", error=str(e), error_type=type(e).__name__
            )
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        await self._get_async_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.async_client:
            await self.async_client.aclose()
            self.async_client = None

    def _make_request(
        self, method: str, url: str, json_data: Optional[Dict] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and circuit breaker protection.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            json_data: JSON payload for POST requests
            **kwargs: Additional request parameters

        Returns:
            Response data as dictionary
        """
        # Check if circuit breaker allows execution
        self.circuit_breaker.can_execute()

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
            self.circuit_breaker.record_success()
            return response.json()

        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(
                "http_request_failed",
                method=method,
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


class LocalProvider(BaseProvider):
    """
    Base class for local/embedded providers.

    Provides common functionality for providers that run models locally:
    - Model loading/unloading
    - Memory management
    - GPU acceleration detection

    Examples: llama.cpp, Ollama (local), vLLM
    """

    DEFAULT_CONFIG = {
        "n_ctx": 4096,
        "n_threads": None,  # Auto-detect
        "n_gpu_layers": 0,
        "verbose": False,
    }

    def __init__(self):
        """Initialize local provider."""
        super().__init__()
        self.model = None  # Loaded on first use
        self.capabilities.local = True

    @abstractmethod
    def _load_model(self):
        """Load the model into memory."""
        pass

    def _ensure_model_loaded(self):
        """Ensure model is loaded before use."""
        if self.model is None:
            self.model = self._load_model()
            logger.info("model_loaded", provider_class=self.__class__.__name__)

    def unload_model(self):
        """Unload model to free memory."""
        if self.model is not None:
            self.model = None
            import gc

            gc.collect()
            logger.info("model_unloaded", provider_class=self.__class__.__name__)

    def __del__(self):
        """Cleanup when provider is destroyed."""
        self.unload_model()


__all__ = [
    "BaseProvider",
    "HTTPProvider",
    "LocalProvider",
    "ProviderCapabilities",
]
