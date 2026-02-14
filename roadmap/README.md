# DocFlow Technical Roadmap

**Status:** Draft
**Last Updated:** 2026-02-14
**Goal:** Transform DocFlow into a production-ready, maintainable document processing system.

## Strategic Phases

This roadmap is organized into sequential phases to address technical debt first, ensuring a stable foundation before expansion.

###  Phase 1: Foundation & Cleanup (Current Focus)
**Goal:** Eliminate redundancy, fix critical architectural flaws, and stabilize the core.
- **M1.1: Architecture Simplification**: Remove duplicate cores, consolidate CLI.
- **M1.2: Model Layer Consolidation**: Unify around OpenRouter (Cloud) + Ollama (Local). Remove redundant implementations.
- **M1.3: Code Hygiene**: Fix error handling, logging, and type safety.
- **M1.4: Configuration & Testing**: Centralize config, fix broken tests.

### Phase 2: Reliability Hardening
**Goal:** Ensure the system runs reliably in production.
- **M2.1: Async Architecture**: Native async implementation (remove `run_in_executor` wrappers).
- **M2.2: Observability**: Structured logging, request tracing, metrics.
- **M2.3: Resilience**: Circuit breakers, retry policies, rate limiting.

### Phase 3: Feature Expansion
**Goal:** Add requested capabilities on top of the stable core.
- **M3.1: Workflow Engine**: DAG-based processing pipelines.
- **M3.2: Advanced Formats**: Native Excel/CSV support, improved Table OCR.
- **M3.3: API Evolution**: Versioned API, OpenAPI schema generation.

### Phase 4: Production Readiness
**Goal:** Deployment and scale.
- **M4.1: Containerization**: Optimized Docker builds.
- **M4.2: CI/CD**: Automated testing and deployment pipelines.
- **M4.3: Security**: AuthZ/AuthN, secret management.
