# Google Tasks Router Refactor Implementation Plan

## Overview

Move all Google Tasks route handlers from `main.py` to a separate `szymon/routers/tasks.py` file using FastAPI's `APIRouter` pattern. This improves code organization and reduces `main.py` from ~259 lines to ~100 lines.

## Current State Analysis

- `szymon/main.py` (259 lines) contains: Settings, service initialization, ALL route handlers
- `szymon/services/google_tasks.py` (200 lines) contains: GoogleTasksService + Pydantic models
- No `routers/` directory exists

### Key Code Locations:
- Service initialization: `szymon/main.py:48-61`
- Helper function `_require_google_tasks()`: `szymon/main.py:108-115`
- Route handlers (11 endpoints): `szymon/main.py:118-235`

## Desired End State

```
szymon/
├── __init__.py
├── main.py              # ~100 lines - FastAPI app, settings, router includes
├── routers/
│   ├── __init__.py
│   └── tasks.py         # ~120 lines - APIRouter + service init + handlers
└── services/
    ├── __init__.py
    └── google_tasks.py  # Unchanged
```

**Verification:**
- Server starts without errors: `szymon` or `uvicorn szymon.main:app --reload`
- All `/api/tasks/*` endpoints work as before (test via `/docs`)
- `main.py` contains no Google Tasks route handlers

## What We're NOT Doing

- NOT modifying `services/google_tasks.py`
- NOT moving Settings to a separate config file
- NOT changing any API behavior or endpoints
- NOT adding new features

## Implementation Approach

Use FastAPI's `APIRouter` with a prefix to define all routes in the new file, then include it in `main.py` with a single `app.include_router()` call. Service initialization happens in `main.py` and is injected into the router module.

---

## Phase 1: Create Router Infrastructure

### Overview
Create the routers package and the tasks router file with all route handlers.

### Changes Required:

#### 1. Create `szymon/routers/__init__.py`
**File**: `szymon/routers/__init__.py` (new)

```python
"""FastAPI routers."""
```

#### 2. Create `szymon/routers/tasks.py`
**File**: `szymon/routers/tasks.py` (new)

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

### Success Criteria:

#### Automated Verification:
- [x] File exists: `ls szymon/routers/tasks.py`
- [x] Python syntax valid: `python -c "import szymon.routers.tasks"`

#### Manual Verification:
- [x] None for this phase (tested in Phase 2)

---

## Phase 2: Update main.py

### Overview
Remove route handlers from `main.py` and include the new router.

### Changes Required:

#### 1. Update `szymon/main.py`
**File**: `szymon/main.py`

Replace the entire file with:

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
            "-cert-file",
            str(settings.ssl_certfile),
            "-key-file",
            str(settings.ssl_keyfile),
            "localhost",
            "127.0.0.1",
            "::1",
            "0.0.0.0",
            hostname,
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

### Success Criteria:

#### Automated Verification:
- [x] Python syntax valid: `python -c "from szymon.main import app"`
- [x] Server starts: `timeout 5 szymon || true` (exits with timeout, not error)

#### Manual Verification:
- [ ] Start server with `szymon` or `uvicorn szymon.main:app --reload`
- [ ] Visit `https://localhost:2137/docs` - all `/api/tasks/*` endpoints visible
- [ ] Test `/api/tasks/auth/status` returns expected response
- [ ] Test `/health` endpoint still works

---

## Testing Strategy

### Automated Tests:
- Import validation: `python -c "from szymon.main import app; from szymon.routers.tasks import router"`

### Manual Testing Steps:
1. Start server: `szymon`
2. Open `https://localhost:2137/docs`
3. Verify all 11 task endpoints are listed under "tasks" tag
4. Test `GET /api/tasks/auth/status` - should return `{"configured": true/false, ...}`
5. Test `GET /health` - should return `{"status": "ok"}`
6. If authenticated, test `GET /api/tasks/lists` - should return task lists

## References

- Research: `thoughts/shared/research/2026-02-01_google-tasks-refactor.md`
- FastAPI Router docs: https://fastapi.tiangolo.com/tutorial/bigger-applications/
