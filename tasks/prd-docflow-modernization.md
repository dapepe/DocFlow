[PRD]
# PRD: DocFlow Modernization & Enhancement

## Overview

Modernize DocFlow document processing system by adding llama.cpp as a high-performance local inference backend, integrating state-of-the-art 2024-2025 vision-language models, and enhancing the architecture with async support and layout-aware processing. This project maintains 100% backwards compatibility while significantly expanding capabilities.

## Goals

- Add llama.cpp backend for direct GGUF model inference (lower overhead than Ollama)
- Integrate modern vision models: Claude 3.7, Gemini 2.0, olmOCR, Qwen2.5-VL
- Maintain 100% backwards compatibility with existing Ollama/OpenRouter models
- Add async support for concurrent document processing
- Implement layout-aware document processing (extract structure, not just text)
- Create unified provider architecture for easier future integrations
- Add intelligent model selection based on document characteristics
- Improve performance through caching, batching, and GPU acceleration

## Quality Gates

These commands must pass for every user story:
- `python -m py_compile docflow/**/*.py` - Syntax validation
- `python -m pytest tests/ -v` - Test suite (if tests exist)
- `python main.py models` - CLI models command works
- `python main.py process testdocs/sample.pdf --model fallback` - Basic processing works

For provider stories, also verify:
- Model registration succeeds
- Model availability detection works
- Information extraction produces valid JSON

## User Stories

### Phase 1: llama.cpp Backend Foundation

#### US-001: Create llama.cpp provider base class
**Description:** As a developer, I want a llama.cpp provider base class so that GGUF models can be integrated with the same interface as Ollama models.

**Acceptance Criteria:**
- [ ] Create `docflow/models/providers/__init__.py` package
- [ ] Create `docflow/models/providers/llama_cpp_provider.py` with `LlamaCppProvider` class
- [ ] Implement `_load_model()` method to load GGUF files using llama-cpp-python
- [ ] Support configurable context window (n_ctx), threads (n_threads), GPU layers (n_gpu_layers)
- [ ] Implement `generate()` method compatible with existing model interface
- [ ] Add automatic model availability detection (check if GGUF file exists)
- [ ] Include proper error handling for missing/corrupt GGUF files
- [ ] Add logging for model loading and inference operations

**Technical Notes:**
- Use `llama-cpp-python` library (`llama_cpp.Llama` class)
- Support chat format for vision models (chat_format="chatml")
- Handle both text-only and vision (multimodal) models
- Store GGUF paths in environment variables (LLAMA_CPP_*_PATH)

#### US-002: Add GGUF model implementations
**Description:** As a user, I want to use popular GGUF vision models so that I can process documents with state-of-the-art local models.

**Acceptance Criteria:**
- [ ] Create `docflow/models/qwen2_5_vl.py` - Qwen2.5-VL GGUF implementation
- [ ] Create `docflow/models/llama3_2_vision.py` - Llama 3.2 Vision GGUF implementation
- [ ] Create `docflow/models/olmocr.py` - olmOCR specialized OCR model
- [ ] Each model inherits from `LlamaCppProvider` base
- [ ] Models registered in ModelRegistry with descriptive names
- [ ] Environment variable configuration for each model's GGUF path
- [ ] Model-specific prompts and instructions via prompt_manager
- [ ] Support image encoding (base64) for vision models

**Technical Notes:**
- Model naming: `qwen2.5-vl`, `llama3.2-vision`, `olmocr-7b`
- Use existing prompt_manager integration for consistency
- Support the same `extract_information(text, image_path)` interface
- Include model capability metadata (vision, multilingual, etc.)

#### US-003: Add quantization auto-detection
**Description:** As a user, I want automatic selection of optimal quantization so that models load with best performance for my hardware.

**Acceptance Criteria:**
- [ ] Create `docflow/models/providers/quantization.py` utility module
- [ ] Implement `detect_available_vram()` function
- [ ] Implement `detect_optimal_quantization(model_size_gb)` function
- [ ] Support Q4_K_M, Q5_K_M, Q8_0, FP16 quantization levels
- [ ] Auto-select based on available VRAM/RAM
- [ ] Allow manual override via environment variable
- [ ] Log selected quantization level on model load

**Technical Notes:**
- Use `pynvml` or `GPUtil` for GPU memory detection (optional dependency)
- Fallback to RAM detection if no GPU available
- Quantization levels: Q4 (smallest, fastest), Q8 (balanced), FP16 (highest quality)

#### US-004: Update configuration and requirements
**Description:** As a developer, I want updated configuration templates so that llama.cpp integration is documented and easy to set up.

**Acceptance Criteria:**
- [ ] Add `llama-cpp-python>=0.3.0` to `requirements.txt`
- [ ] Add optional GPU dependencies: `pynvml>=11.0.0` (optional)
- [ ] Update `env.template.txt` with llama.cpp configuration section
- [ ] Add GGUF model path environment variables (3+ models)
- [ ] Add llama.cpp tuning parameters (n_ctx, n_threads, n_gpu_layers)
- [ ] Fix existing requirements.txt duplicates and ordering
- [ ] Update `config/prompt.txt` with llama.cpp model instructions

**Technical Notes:**
- llama-cpp-python requires cmake and build tools on some platforms
- Document GGUF download sources (HuggingFace, ollama.com/library)
- Include example model URLs in comments

### Phase 2: Modern Vision Models

#### US-005: Add direct Anthropic Claude integration
**Description:** As a user, I want direct Claude API access so that I can use Claude 3.7 Sonnet for document analysis without OpenRouter.

**Acceptance Criteria:**
- [ ] Create `docflow/models/claude_vision.py` - Direct Anthropic integration
- [ ] Implement `ClaudeVisionModel` class using `anthropic` Python SDK
- [ ] Support Claude 3.7 Sonnet vision capabilities
- [ ] Handle image encoding (base64) for vision prompts
- [ ] Support streaming responses (optional for future)
- [ ] Environment variable: `ANTHROPIC_API_KEY`
- [ ] Model availability check via API key presence
- [ ] Register as `claude-3.7-sonnet` in ModelRegistry

**Technical Notes:**
- Use `anthropic>=0.40.0` SDK
- Claude uses different message format than OpenAI
- Support both text and image content blocks

#### US-006: Add direct Google Gemini integration
**Description:** As a user, I want direct Gemini API access so that I can use Gemini 2.0 Flash/Pro for fast multimodal processing.

**Acceptance Criteria:**
- [ ] Create `docflow/models/gemini_vision.py` - Direct Gemini integration
- [ ] Implement `GeminiVisionModel` using `google-generativeai` SDK
- [ ] Support Gemini 2.0 Flash (fast) and Pro (powerful)
- [ ] Handle image input via Gemini's content API
- [ ] Support structured JSON output with response_schema
- [ ] Environment variables: `GOOGLE_API_KEY`, `GEMINI_MODEL`
- [ ] Register models: `gemini-2.0-flash`, `gemini-2.0-pro`

**Technical Notes:**
- Gemini has native JSON mode - use it for structured output
- Flash is ~2x faster than Pro for document processing
- Support both `gemini-2.0-flash-exp` and stable versions

#### US-007: Add specialized OCR models
**Description:** As a user, I want purpose-built OCR models so that text extraction from images is more accurate.

**Acceptance Criteria:**
- [ ] Create `docflow/models/olmocr_model.py` - olmOCR integration (via llama.cpp)
- [ ] Create `docflow/models/docling_local.py` - IBM Docling integration
- [ ] olmOCR optimized for document text extraction
- [ ] Docling for layout-aware extraction
- [ ] Both follow existing BaseModel interface
- [ ] Register as `olmocr-7b` and `docling-local`

**Technical Notes:**
- olmOCR is a 7B model fine-tuned specifically for OCR
- Docling has its own Python package `docling>=2.0`
- Consider Docling as a preprocessor, not a replacement

### Phase 3: Architecture Enhancements

#### US-008: Add async document processing
**Description:** As a user, I want async processing so that multiple documents can be processed concurrently without blocking.

**Acceptance Criteria:**
- [ ] Add `async def process_document_async()` method to `DocumentProcessor`
- [ ] Create async versions of text extraction methods
- [ ] Support concurrent model inference where thread-safe
- [ ] Update API endpoints to use async handlers properly
- [ ] Add `asyncio.gather()` for batch processing
- [ ] Maintain backwards compatibility with sync methods
- [ ] Add `aiohttp` for async HTTP requests (API models)

**Technical Notes:**
- llama.cpp is synchronous - use `asyncio.to_thread()` wrapper
- API models can benefit from `aiohttp` ClientSession
- Keep existing sync API for compatibility

#### US-009: Create unified provider architecture
**Description:** As a developer, I want a unified provider system so that adding new backends requires minimal code.

**Acceptance Criteria:**
- [ ] Create `docflow/models/providers/base_provider.py` abstract base
- [ ] Create `docflow/models/providers/http_provider.py` for API-based models
- [ ] Refactor `OllamaBaseModel` to use `HTTPProvider`
- [ ] Refactor `OpenRouterBaseModel` to use `HTTPProvider`
- [ ] Ensure all providers implement same interface
- [ ] Provider handles connection pooling, retries, auth
- [ ] Document provider implementation guide

**Technical Notes:**
- Base provider defines: `generate()`, `is_available()`, `get_capabilities()`
- HTTP provider adds: session management, rate limiting
- Keep existing model classes as thin wrappers

#### US-010: Implement layout-aware processing
**Description:** As a user, I want document structure extraction so that tables, sections, and layout are preserved.

**Acceptance Criteria:**
- [ ] Create `docflow/layout_processor.py` module
- [ ] Implement `extract_layout()` function using pdfplumber or pymupdf
- [ ] Extract: sections (headers, paragraphs), tables, figures
- [ ] Add bounding box information for each element
- [ ] Integrate with existing DocumentProcessor
- [ ] Add `extract_structure=True` parameter
- [ ] Include layout data in output JSON

**Technical Notes:**
- Use `pdfplumber>=0.11.0` or `pymupdf>=1.24.0`
- Store layout as list of elements with type and bbox
- Consider Docling for advanced layout detection

#### US-011: Add intelligent model routing
**Description:** As a user, I want automatic model selection so that the best model is chosen based on document type.

**Acceptance Criteria:**
- [ ] Create `docflow/model_router.py` module
- [ ] Implement `ModelRouter` class
- [ ] Add document characteristics detection (type, language, has_images)
- [ ] Map characteristics to optimal model
- [ ] Support `model=auto` parameter
- [ ] Add routing rules configuration
- [ ] Log routing decisions

**Technical Notes:**
- Invoice → Specialized invoice model or Claude 3.7
- Image-heavy → Vision model with strong OCR
- Multilingual → Qwen2.5-VL or similar
- Fast processing → Gemini Flash or small local model

### Phase 4: Performance & Polish

#### US-012: Enhance caching and performance
**Description:** As a user, I want better caching so that repeated processing of similar documents is faster.

**Acceptance Criteria:**
- [ ] Enhance `PerformanceCache` with content-based hashing
- [ ] Add image fingerprinting for vision model cache keys
- [ ] Implement tiered caching (memory + disk for large items)
- [ ] Add cache statistics endpoint
- [ ] Support cache warming for known document types
- [ ] Add cache TTL configuration per model

#### US-013: Add comprehensive CLI features
**Description:** As a user, I want enhanced CLI capabilities so that I can benchmark models and manage configurations.

**Acceptance Criteria:**
- [ ] Add `docflow benchmark` command to compare models
- [ ] Add `docflow config` command to validate and show config
- [ ] Add `docflow download-model` to fetch GGUF files
- [ ] Enhance `docflow models` with capability display
- [ ] Add progress bars for long-running operations
- [ ] Support JSON output for scripting

#### US-014: Update documentation and examples
**Description:** As a user, I want updated documentation so that I can understand and use new features.

**Acceptance Criteria:**
- [ ] Update README.md with llama.cpp setup instructions
- [ ] Add `docs/llama-cpp-setup.md` detailed guide
- [ ] Add `docs/model-comparison.md` with benchmarks
- [ ] Update `docs/` with new model examples
- [ ] Add migration guide for existing users
- [ ] Include GGUF download links and recommendations

## Functional Requirements

### Core Functionality

- **FR-001:** System must support both Ollama and llama.cpp backends simultaneously
- **FR-002:** GGUF models must load via llama-cpp-python with configurable parameters
- **FR-003:** All models must implement `extract_information(text, image_path)` interface
- **FR-004:** Model availability must be checked via `is_available()` class method
- **FR-005:** System must auto-detect optimal quantization based on available memory
- **FR-006:** Direct API integrations (Anthropic, Gemini) must not require OpenRouter
- **FR-007:** Async processing must not break existing synchronous API
- **FR-008:** Layout extraction must provide structured output (sections, tables, bboxes)

### Configuration

- **FR-009:** All model paths must be configurable via environment variables
- **FR-010:** llama.cpp parameters (n_ctx, n_threads, n_gpu_layers) must be configurable
- **FR-011:** Model routing rules must be configurable via YAML or environment
- **FR-012:** Cache settings (TTL, max_size, disk_path) must be configurable

### Performance

- **FR-013:** llama.cpp models must load faster than Ollama equivalents (no daemon overhead)
- **FR-014:** Async batch processing must handle 10+ documents concurrently
- **FR-015:** Response caching must reduce repeated processing time by 80%+
- **FR-016:** GPU acceleration must be automatically utilized when available

### Compatibility

- **FR-017:** All existing Ollama models must continue working without changes
- **FR-018:** All existing OpenRouter models must continue working without changes
- **FR-019:** Existing environment variables must retain their function
- **FR-020:** API responses must maintain current JSON schema

## Non-Goals (Out of Scope)

- **NG-001:** Cloud deployment infrastructure (K8s, Docker Swarm) - out of scope
- **NG-002:** Web UI dashboard - keep CLI and API focus
- **NG-003:** Real-time collaborative editing - not a document editor
- **NG-004:** Mobile app development - server-side only
- **NG-005:** Fine-tuning custom models - use existing models only
- **NG-006:** Blockchain/verification features - not needed for this scope
- **NG-007:** Multi-tenant user management - single-user focused

## Technical Considerations

### Dependencies

**New Required:**
- `llama-cpp-python>=0.3.0` - Core llama.cpp bindings
- `anthropic>=0.40.0` - Claude API SDK
- `aiohttp>=3.9.0` - Async HTTP client (for API models)

**New Optional:**
- `pynvml>=11.0.0` - GPU memory detection
- `pdfplumber>=0.11.0` - Layout extraction
- `pymupdf>=1.24.0` - Alternative PDF processing

**Updated:**
- Fix `requirements.txt` duplicates and order
- Ensure all versions are compatible with Python 3.11+

### Architecture Decisions

1. **Provider Pattern:** Unified base provider allows easy addition of new backends (vLLM, TGI, etc.)
2. **Async Wrapper:** llama.cpp is sync-only, wrap with `asyncio.to_thread()` for API compatibility
3. **Lazy Loading:** Load models on first use, not at startup, to reduce memory pressure
4. **Plugin Registration:** Keep existing `ModelRegistry.register()` pattern for consistency
5. **Environment Config:** Continue using `.env` pattern, extend for new models

### Performance Targets

- Model load time: <5 seconds for 7B models on SSD
- First inference: <3 seconds (including model load)
- Subsequent inferences: <1 second for text, <3 seconds for vision
- Batch processing: 5+ docs/second with async
- Cache hit rate: >60% for repetitive document types

### Security Considerations

- API keys in environment variables (existing pattern)
- No model downloads without explicit user action
- Validate GGUF file integrity before loading
- Sanitize document text to prevent prompt injection

## Success Metrics

- **SM-001:** All 14 user stories completed and tested
- **SM-002:** llama.cpp models achieve 95%+ accuracy vs Ollama equivalents
- **SM-003:** Processing latency reduced by 30%+ for local models
- **SM-004:** Zero breaking changes to existing Ollama/OpenRouter workflows
- **SM-005:** New model integration time <30 minutes for future models
- **SM-006:** Test coverage >70% for new provider code
- **SM-007:** Documentation completeness: setup, API reference, examples

## Open Questions

- **OQ-001:** Should we bundle small GGUF models with the repository? (Adds ~5GB)
- **OQ-002:** Do we need Windows-specific installation instructions for llama.cpp?
- **OQ-003:** Should we add a model marketplace/discovery feature?
- **OQ-004:** Is GPU acceleration priority for AMD/Intel GPUs or just CUDA?
- **OQ-005:** Should we deprecate any older models in favor of newer alternatives?

## Implementation Timeline

### Week 1: Foundation
- US-001: llama.cpp provider base
- US-004: Configuration updates

### Week 2: Models
- US-002: GGUF model implementations
- US-003: Quantization auto-detection

### Week 3: APIs
- US-005: Claude integration
- US-006: Gemini integration
- US-007: OCR models

### Week 4: Architecture
- US-008: Async support
- US-009: Unified providers

### Week 5: Advanced Features
- US-010: Layout processing
- US-011: Model routing

### Week 6: Polish
- US-012: Caching enhancements
- US-013: CLI improvements
- US-014: Documentation

---

**Next Steps:** Convert this PRD to ralph-tui tasks using `/ralph-tui-create-beads` or `/ralph-tui-create-json`
[/PRD]
