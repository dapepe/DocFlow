# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-14
**Context:** DocFlow Document Processing System

## OVERVIEW
DocFlow is a hybrid Python/Node.js document processing system using FastAPI and Click. It orchestrates text extraction (PDF, DOCX, OCR) and metadata analysis via a plugin-based AI model architecture (Ollama, OpenRouter, Direct APIs).

## STRUCTURE
```
.
├── docflow/                 # Core application package
│   ├── models/              # AI Model implementations & Registry
│   │   └── providers/       # Abstract provider interfaces
│   ├── cli.py               # Main CLI entry point
│   ├── api.py               # FastAPI server endpoints
│   └── processor.py         # Main processing pipeline
├── config/                  # Configuration (rules.yaml, prompt.txt)
├── tests/                   # Pytest suite
└── main.py                  # Entry point wrapper
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Entry Point** | `main.py` | Delegates to `docflow.cli` |
| **Core Logic** | `docflow/processor.py` | Text extraction & orchestration |
| **Model Registry** | `docflow/models/__init__.py` | Dynamic loading & availability checks |
| **API Routes** | `docflow/api.py` | FastAPI endpoints |
| **CLI Commands** | `docflow/cli.py` | Click command groups |
| **Config** | `config/` | Rules, schemas, and prompts |

## CONVENTIONS
*   **Logging**: ALWAYS use `logger = logging.getLogger(__name__)`. NEVER use `print()`.
*   **Async/Sync**: API (`api.py`) is `async`. Models are synchronous; `processor.py` wraps them in `run_in_executor`.
*   **Configuration**: Hybrid approach. `config/` for static rules, `.env` for secrets/settings.
*   **Imports**: Absolute imports preferred within `docflow`.

## ANTI-PATTERNS (THIS PROJECT)
*   **Duplicate Core**: `docflow/core.py` is legacy/duplicate. USE `docflow/processor.py`.
*   **Bare Exceptions**: DO NOT use `except:` without exception type.
*   **Hardcoded Fallbacks**: Avoid "Always fallback" logic without logging/metrics.
*   **Shell Scripts**: Avoid modifying `.sh` wrappers; prefer Python entry points.

## COMMANDS
```bash
# Run API Server
python main.py serve --host 0.0.0.0 --port 8000

# Process Document (CLI)
python main.py process path/to/doc.pdf --model qwen-vision

# Benchmark Models
python main.py benchmark --document test.pdf --models qwen2.5-vl claude-vision

# Check Configuration
python main.py config

# Run Tests
pytest tests/
```

## ARCHITECTURE NOTES
*   **Model Plugin System**: Models self-register via `ModelRegistry`.
*   **Unified Provider**: All models inherit from `BaseProvider`, with specialized `HTTPProvider` (Ollama, OpenRouter) and `LocalProvider` (llama.cpp, Docling).
*   **Async Core**: `processor.py` and `api.py` fully support async/await for high concurrency.
*   **Routing**: `ModelRouter` selects models based on document type (e.g., invoices -> Claude, simple -> Flash).
*   **Dual-Core Issue**: `core.py` and `processor.py` exist. `processor.py` is the active implementation.
*   **Hybrid Config**: Node.js `package.json` exists but project is primarily Python.

## MODERNIZATION UPDATE (FEB 2026)
Successfully completed the DocFlow Modernization initiative (`DocFlow-nty`).

### Key Implementations
1.  **Native llama.cpp Support**:
    *   `LlamaCppProvider` base class with GGUF loading and auto-GPU offload.
    *   Models: `qwen2.5-vl`, `llama3.2-vision`, `olmocr-7b`.
    *   Quantization awareness and VRAM detection.

2.  **Direct Cloud Integrations**:
    *   `ClaudeVisionModel` (Anthropic SDK) for high-reasoning tasks.
    *   `GeminiVisionModel` (Google GenAI SDK) for high-speed/volume tasks.

3.  **Architecture Overhaul**:
    *   **Async Processing**: Full async pipeline in `process_document_async` and batch endpoints.
    *   **Unified Providers**: Refactored `Ollama` and `OpenRouter` to use shared `HTTPProvider` logic.
    *   **Layout Awareness**: `LayoutProcessor` via `pdfplumber` for table/section extraction.
    *   **Intelligent Routing**: `ModelRouter` dynamically selects models based on document content.

4.  **Tooling & Performance**:
    *   **CLI**: Added `benchmark`, `config`, and capabilities view to `models`.
    *   **Caching**: SHA-256 content hashing for robust response caching.
    *   **Metrics**: Performance monitoring for request latency and success rates.

### Verification Status
*   All new models (`Claude`, `Gemini`, `Qwen`, `Llama`, `Docling`) registered and loadable.
*   `requirements.txt` updated with `llama-cpp-python`, `anthropic`, `google-generativeai`.
*   CLI commands verified and operational.
*   Async batch processing verified in API.

### Future Recommendations
*   **Deprecate Legacy Core**: Remove `docflow/core.py` as it is superseded by `processor.py`.
*   **Frontend**: Consider a React/Next.js frontend for the API (currently CLI/API only).
*   **Vector Store**: Add RAG capabilities for document querying.


## Repository Management Guidelines

This skill manages project work using **git-beads** via the `bd` CLI: epics, tasks, sub-tasks, statuses, priorities, labels, and dependency edges. Use it whenever the user asks to create, list, modify, update, triage, or restructure Beads.

### Operating principles

- **Beads is the source of truth** for epics/tasks. Don’t create parallel task systems.
- **Read before write**: show/list an issue before changing it (unless user says “force”).
- Prefer **structured outputs** (`--json`) when available.
- Avoid duplicates: search/list for similar issues first; if found, link as `related` instead of creating.
- Changes should be **idempotent**: safe to re-run without creating duplicates or flipping states incorrectly.

### Agent Rules for Beads

- Prometheus is a READ-ONLY planner and CANNOT use `bash`.
- To interact with tasks, Prometheus MUST use the specialized Beads tools:
  - `beads_list_ready()` instead of `bd ready`
  - `beads_query()` instead of `bd list`
  - `beads_get_task()` instead of `bd show`
- If you need to sync or create beads, include those as commands in your Plan file for Sisyphus to execute later.


### Data contracts (preferred internal representations)

#### IssueCreate (canonical)

```json
{
  "title": "string",
  "priority": 0,
  "labels": ["epic|bug|chore|docs|test|refactor"],
  "notes": "string",
  "parent": "bd-1234",
  "blocked_by": ["bd-1","bd-2"],
  "type": "epic|task"
}
```

#### IssuePatch (canonical)

```json
{
  "id": "bd-1234",
  "fields": {
    "title": "string?",
    "status": "open|in_progress|blocked|done?",
    "priority": 0,
    "labels": ["..."] ,
    "notes": "string?"
  },
  "deps_add": [{"type":"blocked_by|related|parent|discovered-from","from":"bd-x","to":"bd-y"}],
  "deps_rm":  [{"type":"blocked_by|related|parent|discovered-from","from":"bd-x","to":"bd-y"}]
}
```

#### IssueSummary (canonical)

```json
{
  "id":"bd-1234",
  "title":"string",
  "status":"open|in_progress|blocked|done",
  "priority":2,
  "labels":["..."],
  "parent":"bd-1?",
  "blocked_by":["..."],
  "blocks":["..."]
}
```

When responding, prefer producing IssueSummary JSON for the issues touched.


### Conventions (Beads-only, opinionated defaults)

Priorities (P0–P4)
- P0: urgent production break / security / data loss / hard blocker
- P1: critical path for next milestone
- P2: important but not blocking milestone
- P3: nice-to-have / backlog
- P4: speculative / maybe later

Statuses + transitions (if supported)
- open → in_progress → done
- Use blocked only when there is at least one blocked_by dependency (or explicit reason in notes).
- Don’t set done if acceptance criteria are unknown—create a clarification task instead.

Labels (recommended): epic, bug, chore, docs, test, refactor

<!-- bv-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View issues (launches TUI - avoid in automated sessions)
bv

# CLI commands for agents (use these instead)
bd ready              # Show issues ready to work (no blockers)
bd list --status=open # All open issues
bd show <id>          # Full issue details with dependencies
bd create --title="..." --type=task --priority=2
bd update <id> --status=in_progress
bd close <id> --reason="Completed"
bd close <id1> <id2>  # Close multiple issues at once
bd sync               # Commit and push changes
```

### Workflow Pattern

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `bd close <id>`
5. **Sync**: Always run `bd sync` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)
- **Types**: task, bug, feature, epic, question, docs
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
bd sync                 # Commit beads changes
git commit -m "..."     # Commit code
bd sync                 # Commit any new beads changes
git push                # Push to remote
```

### Best Practices

- Check `bd ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `bd create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always `bd sync` before ending session

<!-- end-bv-agent-instructions -->
