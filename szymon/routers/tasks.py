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
