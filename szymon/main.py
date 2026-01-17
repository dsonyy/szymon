import socket
import subprocess
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic_settings import BaseSettings, SettingsConfigDict

from szymon.services.google_tasks import GoogleTasksService, TaskCreate, TaskUpdate

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


def get_google_tasks_redirect_uri() -> str:
    """Get the OAuth redirect URI based on server settings."""
    return f"https://localhost:{settings.port}/api/tasks/auth/callback"


# Initialize Google Tasks service
google_tasks: Optional[GoogleTasksService] = None
if settings.google_client_id and settings.google_client_secret:
    google_tasks = GoogleTasksService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_path=settings.google_token_path,
        redirect_uri=get_google_tasks_redirect_uri(),
    )


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


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ASSETS_DIR / "favicon.gif", media_type="image/gif")


@app.get("/health")
def health():
    return {"status": "ok"}


# Google Tasks API routes


def _require_google_tasks() -> GoogleTasksService:
    """Helper to check if Google Tasks is configured."""
    if google_tasks is None:
        raise HTTPException(
            status_code=503,
            detail="Google Tasks not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env",
        )
    return google_tasks


@app.get("/api/tasks/auth/status")
def tasks_auth_status():
    """Check if Google Tasks is authenticated."""
    if google_tasks is None:
        return {"configured": False, "authenticated": False}
    return {"configured": True, "authenticated": google_tasks.is_authenticated()}


@app.get("/api/tasks/auth/login")
def tasks_auth_login():
    """Redirect to Google OAuth login."""
    from fastapi.responses import RedirectResponse
    service = _require_google_tasks()
    url, state = service.get_auth_url()
    return RedirectResponse(url=url)


@app.get("/api/tasks/auth/callback")
def tasks_auth_callback(code: str, state: Optional[str] = None):
    """OAuth callback - exchange code for tokens."""
    from fastapi.responses import HTMLResponse
    service = _require_google_tasks()
    try:
        service.exchange_code(code)
        return HTMLResponse(
            content="""
            <html><body>
            <h1>Authentication successful!</h1>
            <p>You can close this window and return to the app.</p>
            <script>window.close();</script>
            </body></html>
            """,
            status_code=200,
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h1>Authentication failed</h1><p>{e}</p></body></html>",
            status_code=400,
        )


@app.get("/api/tasks/lists")
def list_task_lists():
    """List all task lists."""
    service = _require_google_tasks()
    try:
        return service.list_task_lists()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks")
def list_tasks(
    task_list_id: str = "@default",
    show_completed: bool = True,
):
    """List all tasks in a task list."""
    service = _require_google_tasks()
    try:
        return service.list_tasks(
            task_list_id=task_list_id,
            show_completed=show_completed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, task_list_id: str = "@default"):
    """Get a specific task."""
    service = _require_google_tasks()
    try:
        return service.get_task(task_id, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks")
def create_task(task: TaskCreate, task_list_id: str = "@default"):
    """Create a new task."""
    service = _require_google_tasks()
    try:
        return service.create_task(task, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/tasks/{task_id}")
def update_task(task_id: str, task: TaskUpdate, task_list_id: str = "@default"):
    """Update an existing task."""
    service = _require_google_tasks()
    try:
        return service.update_task(task_id, task, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str, task_list_id: str = "@default"):
    """Delete a task."""
    service = _require_google_tasks()
    try:
        service.delete_task(task_id, task_list_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: str, task_list_id: str = "@default"):
    """Mark a task as completed."""
    service = _require_google_tasks()
    try:
        return service.complete_task(task_id, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/uncomplete")
def uncomplete_task(task_id: str, task_list_id: str = "@default"):
    """Mark a task as not completed."""
    service = _require_google_tasks()
    try:
        return service.uncomplete_task(task_id, task_list_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
