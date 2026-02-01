---
date: 2026-02-01T15:41:56+01:00
researcher: Claude
git_commit: 5c281a1aff0924d74489da3b1eac9f3d73984952
branch: main
repository: szymon
topic: "Python to Go rewrite analysis"
tags: [research, codebase, architecture, language-comparison, go, python]
status: complete
last_updated: 2026-02-01
last_updated_by: Claude
---

# Research: Should Szymon be rewritten from Python to Go?

**Date**: 2026-02-01T15:41:56+01:00
**Researcher**: Claude
**Git Commit**: 5c281a1aff0924d74489da3b1eac9f3d73984952
**Branch**: main
**Repository**: szymon

## Research Question
Does it make sense to rewrite the Szymon personal assistant from Python to Go? What are the pros and cons?

## Summary

**Recommendation: No, a Go rewrite does not make sense for this project.**

The codebase is small (~460 lines of Python), uses Python-specific libraries with excellent Google API support, and serves as a personal assistant/API gateway where Python's rapid prototyping benefits outweigh Go's performance advantages. The effort-to-benefit ratio strongly favors staying with Python.

## Detailed Findings

### Current Codebase Analysis

| Metric | Value |
|--------|-------|
| Total Python LOC | ~460 lines (excluding empty `__init__.py` files) |
| Main files | 2 (`main.py`: 258 lines, `google_tasks.py`: 199 lines) |
| Framework | FastAPI with uvicorn |
| External APIs | Google Tasks API via `google-api-python-client` |
| Auth | OAuth2 via `google-auth-oauthlib` |
| Config | pydantic-settings (`.env` loading) |
| Frontend | Static React app served by FastAPI |

### Pro: Arguments FOR Rewriting to Go

1. **Single Binary Distribution**
   - Go compiles to a single static binary
   - No Python interpreter or virtualenv required
   - Easier deployment, especially on minimal systems

2. **Memory Footprint**
   - Go typically uses 5-10x less memory at idle
   - For a personal assistant running 24/7, this could matter on resource-constrained devices

3. **Startup Time**
   - Go binaries start in milliseconds
   - Python+uvicorn has noticeable startup lag (~1-2s)

4. **Type Safety**
   - Go has compile-time type checking (though Python has pydantic + mypy)
   - Catches more errors before runtime

5. **Concurrency Model**
   - Goroutines are lightweight and built-in
   - Python's asyncio is functional but more complex

6. **Cross-Compilation**
   - Go easily cross-compiles for ARM, Windows, etc.
   - Useful if deploying to Raspberry Pi or similar

### Con: Arguments AGAINST Rewriting to Go

1. **Google API Client Libraries**
   - Python's `google-api-python-client` is first-party, well-maintained, and feature-complete
   - Go's Google API client exists but has less community support
   - OAuth2 flows are more ergonomic in Python with `google-auth-oauthlib`

2. **Development Velocity**
   - Python excels at rapid prototyping
   - This is a personal project—iteration speed matters more than production hardening
   - Adding new integrations (more Google APIs, other services) is faster in Python

3. **Codebase Size**
   - ~460 lines is trivially small
   - A rewrite would take significant effort for marginal gain
   - The existing code is clean and maintainable

4. **FastAPI Ecosystem**
   - FastAPI provides automatic OpenAPI/Swagger docs at `/docs`
   - Pydantic models give automatic validation and serialization
   - Go equivalents (gin, echo, fiber) lack this seamless integration

5. **Hot Reload**
   - `uvicorn --reload` provides instant feedback during development
   - Go requires recompilation (though tools like `air` help)

6. **Existing Tooling**
   - pyproject.toml, hatchling build system already set up
   - mkcert integration for SSL certificates works well
   - Justfile for task running is language-agnostic

7. **MCP/AI Integration**
   - The project description mentions "designed for AI, MCP integrations"
   - Python dominates the AI/ML ecosystem
   - Future integrations with LLM tools, embeddings, etc. will be easier in Python

8. **Maintenance Burden**
   - Rewriting means maintaining two codebases or abandoning working code
   - Personal projects often stall after major rewrites

### Cost-Benefit Analysis

| Factor | Python (current) | Go (hypothetical) |
|--------|-----------------|-------------------|
| Development speed | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Google API support | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Memory usage | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Deployment simplicity | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| AI/ML ecosystem | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Rewrite effort | N/A | ~1-2 days |

### When Go WOULD Make Sense

A Go rewrite would be justified if:
- The project needed to handle thousands of concurrent connections
- Deployment to many heterogeneous systems was required
- The codebase grew to 10,000+ lines with multiple contributors
- Memory constraints were critical (embedded systems)
- The Google APIs were replaced with custom/simpler protocols

## Code References

- `szymon/main.py:1-258` - FastAPI application, settings, routes
- `szymon/services/google_tasks.py:1-199` - Google Tasks OAuth and CRUD
- `pyproject.toml:1-24` - Dependencies and build configuration

## Architecture Insights

The current architecture is well-suited for Python:
- **Settings via pydantic-settings** (line 20-42) - Go equivalent would require manual parsing or third-party libs
- **OAuth2 flow** (google_tasks.py:51-114) - Python's `Flow` class handles complexity elegantly
- **Type hints + Pydantic models** - Provide Go-like type safety with Python flexibility
- **Static file serving** (main.py:239-240) - Serves React frontend seamlessly

## Open Questions

1. Are there specific performance requirements not yet apparent?
2. Is deployment to resource-constrained devices planned?
3. Will this project be used by others beyond personal use?
4. Are there planned integrations that Go handles better (gRPC, protobuf)?

## Conclusion

For a personal assistant project of this scope, Python is the pragmatic choice. The rewrite effort would take 1-2 days for marginal benefits that don't address actual pain points. If specific needs arise (deployment, memory, scale), revisit this decision then.

**Verdict: Stay with Python.**
