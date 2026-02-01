---
date: 2026-02-01T12:00:00+00:00
researcher: Claude
git_commit: 5c281a1aff0924d74489da3b1eac9f3d73984952
branch: main
repository: szymon
topic: "Refactoring Google Tasks routes to separate service file"
tags: [research, codebase, google-tasks, refactoring, fastapi, routers]
status: complete
last_updated: 2026-02-01
last_updated_by: Claude
---

# Research: Refactoring Google Tasks Routes to Separate Service File

**Date**: 2026-02-01
**Researcher**: Claude
**Git Commit**: 5c281a1aff0924d74489da3b1eac9f3d73984952
**Branch**: main
**Repository**: szymon

## Research Question

Move all Google Tasks logic to a separate 1-file service, keeping only the routing definition in main.py.

## Summary

The current implementation has:
- **Service logic** already in `szymon/services/google_tasks.py` (lines 1-199)
- **Route handlers** in `szymon/main.py` (lines 108-235)
- **Service initialization** in `szymon/main.py` (lines 48-61)

The recommended approach is to use **FastAPI's APIRouter** to define routes in a separate file (`szymon/routers/tasks.py`) and include it in main.py with a single line.

## Detailed Findings

### Current Structure

```
szymon/
├── __init__.py
├── main.py              # 259 lines - FastAPI app, settings, ALL route handlers
└── services/
    ├── __init__.py
    └── google_tasks.py  # 199 lines - GoogleTasksService + Pydantic models
```

### What Needs to Move

From `main.py`, the following should move to a new router file:

1. **Service initialization** (lines 48-61):
   ```python
   def get_google_tasks_redirect_uri() -> str:
       return f"https://localhost:{settings.port}/api/tasks/auth/callback"

   google_tasks: Optional[GoogleTasksService] = None
   if settings.google_client_id and settings.google_client_secret:
       google_tasks = GoogleTasksService(...)
   ```

2. **Helper function** (lines 108-115):
   ```python
   def _require_google_tasks() -> GoogleTasksService:
       ...
   ```

3. **All route handlers** (lines 118-235):
   - `tasks_auth_status()` - GET `/api/tasks/auth/status`
   - `tasks_auth_login()` - GET `/api/tasks/auth/login`
   - `tasks_auth_callback()` - GET `/api/tasks/auth/callback`
   - `list_task_lists()` - GET `/api/tasks/lists`
   - `list_tasks()` - GET `/api/tasks`
   - `get_task()` - GET `/api/tasks/{task_id}`
   - `create_task()` - POST `/api/tasks`
   - `update_task()` - PUT `/api/tasks/{task_id}`
   - `delete_task()` - DELETE `/api/tasks/{task_id}`
   - `complete_task()` - POST `/api/tasks/{task_id}/complete`
   - `uncomplete_task()` - POST `/api/tasks/{task_id}/uncomplete`

### Proposed New Structure

```
szymon/
├── __init__.py
├── main.py              # FastAPI app, settings, router includes
├── routers/
│   ├── __init__.py
│   └── tasks.py         # Google Tasks APIRouter + service init + handlers
└── services/
    ├── __init__.py
    └── google_tasks.py  # GoogleTasksService + Pydantic models (unchanged)
```

### Implementation Plan

#### 1. Create `szymon/routers/tasks.py`

```python
"""Google Tasks API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from szymon.services.google_tasks import GoogleTasksService, TaskCreate, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Service instance (initialized from main.py)
_service: Optional[GoogleTasksService] = None


def init_service(service: Optional[GoogleTasksService]) -> None:
    """Initialize the Google Tasks service. Called from main.py."""
    global _service
    _service = service


def _require_service() -> GoogleTasksService:
    """Helper to check if Google Tasks is configured."""
    if _service is None:
        raise HTTPException(
            status_code=503,
            detail="Google Tasks not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env",
        )
    return _service


@router.get("/auth/status")
def auth_status():
    """Check if Google Tasks is authenticated."""
    if _service is None:
        return {"configured": False, "authenticated": False}
    return {"configured": True, "authenticated": _service.is_authenticated()}


@router.get("/auth/login")
def auth_login():
    """Redirect to Google OAuth login."""
    service = _require_service()
    url, state = service.get_auth_url()
    return RedirectResponse(url=url)


@router.get("/auth/callback")
def auth_callback(code: str, state: Optional[str] = None):
    """OAuth callback - exchange code for tokens."""
    service = _require_service()
    try:
        service.exchange_code(code)
        return RedirectResponse(url="/")
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h1>Authentication failed</h1><p>{e}</p></body></html>",
            status_code=400,
        )


@router.get("/lists")
def list_task_lists():
    """List all task lists."""
    service = _require_service()
    try:
        return service.list_task_lists()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def list_tasks(task_list_id: str = "@default", show_completed: bool = True):
    """List all tasks in a task list."""
    service = _require_service()
    try:
        return service.list_tasks(task_list_id=task_list_id, show_completed=show_completed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}")
def get_task(task_id: str, task_list_id: str = "@default"):
    """Get a specific task."""
    service = _require_service()
    try:
        return service.get_task(task_id, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_task(task: TaskCreate, task_list_id: str = "@default"):
    """Create a new task."""
    service = _require_service()
    try:
        return service.create_task(task, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{task_id}")
def update_task(task_id: str, task: TaskUpdate, task_list_id: str = "@default"):
    """Update an existing task."""
    service = _require_service()
    try:
        return service.update_task(task_id, task, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
def delete_task(task_id: str, task_list_id: str = "@default"):
    """Delete a task."""
    service = _require_service()
    try:
        service.delete_task(task_id, task_list_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/complete")
def complete_task(task_id: str, task_list_id: str = "@default"):
    """Mark a task as completed."""
    service = _require_service()
    try:
        return service.complete_task(task_id, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/uncomplete")
def uncomplete_task(task_id: str, task_list_id: str = "@default"):
    """Mark a task as not completed."""
    service = _require_service()
    try:
        return service.uncomplete_task(task_id, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 2. Update `szymon/main.py`

```python
import socket
import subprocess
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic_settings import BaseSettings, SettingsConfigDict

from szymon.routers import tasks as tasks_router
from szymon.services.google_tasks import GoogleTasksService

ROOT_DIR = Path(__file__).parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
CERTS_DIR = ROOT_DIR / "certs"
WEB_DIR = ROOT_DIR / "web" / "dist"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    app_name: str = "szymon"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 2137

    # Google Tasks API
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None

    @property
    def ssl_certfile(self) -> Path:
        return CERTS_DIR / "cert.pem"

    @property
    def ssl_keyfile(self) -> Path:
        return CERTS_DIR / "key.pem"

    @property
    def google_token_path(self) -> Path:
        return ROOT_DIR / ".google_token.json"


settings = Settings()


def _init_google_tasks() -> Optional[GoogleTasksService]:
    """Initialize Google Tasks service if configured."""
    if not settings.google_client_id or not settings.google_client_secret:
        return None
    redirect_uri = f"https://localhost:{settings.port}/api/tasks/auth/callback"
    return GoogleTasksService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_path=settings.google_token_path,
        redirect_uri=redirect_uri,
    )


# Initialize services and routers
tasks_router.init_service(_init_google_tasks())


def ensure_certs():
    """Generate SSL certificates with mkcert if they don't exist."""
    if settings.ssl_certfile.exists() and settings.ssl_keyfile.exists():
        return
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating SSL certificates with mkcert...")
    hostname = socket.gethostname()
    subprocess.run(
        [
            "mkcert",
            "-cert-file", str(settings.ssl_certfile),
            "-key-file", str(settings.ssl_keyfile),
            "localhost", "127.0.0.1", "::1", "0.0.0.0", hostname,
        ],
        check=True,
    )


app = FastAPI(
    title=settings.app_name,
    description="Personal assistant - gateway for personal APIs and tools",
)

# Include routers
app.include_router(tasks_router.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ASSETS_DIR / "favicon.gif", media_type="image/gif")


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve React app - must be after API routes
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


def main():
    ensure_certs()
    print(f"Starting {settings.app_name} on https://{settings.host}:{settings.port}")
    uvicorn.run(
        "szymon.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
        ssl_certfile=str(settings.ssl_certfile),
        ssl_keyfile=str(settings.ssl_keyfile),
    )


if __name__ == "__main__":
    main()
```

#### 3. Create `szymon/routers/__init__.py`

```python
# Empty file - makes routers a package
```

## Code References

- `szymon/main.py:48-61` - Current service initialization
- `szymon/main.py:108-115` - Current `_require_google_tasks()` helper
- `szymon/main.py:118-235` - All Google Tasks route handlers
- `szymon/services/google_tasks.py:1-199` - GoogleTasksService (remains unchanged)

## Architecture Insights

1. **FastAPI Router Pattern**: Using `APIRouter` with a prefix (`/api/tasks`) keeps routes organized and allows clean separation
2. **Service Injection**: The `init_service()` pattern allows main.py to configure the service while keeping routes decoupled
3. **Single File Goal**: All route handlers + service management fit in one file (~120 lines)
4. **Settings Remain in main.py**: Configuration stays centralized in main.py where it's needed for other services

## Benefits of This Refactoring

1. **main.py reduced from ~259 to ~100 lines**
2. **All Google Tasks logic in one place** (`routers/tasks.py`)
3. **Easy to add more routers** for future services
4. **Clean separation** between app setup and route logic
5. **Service unchanged** - GoogleTasksService in services/ remains as-is

## Open Questions

1. Should Settings also move to a separate file (e.g., `szymon/config.py`)?
2. Should the router file be named `google_tasks.py` to match the service, or `tasks.py` for brevity?
