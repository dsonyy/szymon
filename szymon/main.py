import logging
import socket
import subprocess
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

from szymon.routers import calendar as calendar_router
from szymon.routers import tasks as tasks_router
from szymon.services.google_auth import GoogleAuthService
from szymon.services.google_calendar import GoogleCalendarService
from szymon.services.google_tasks import GoogleTasksService

ROOT_DIR = Path(__file__).parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
CERTS_DIR = ROOT_DIR / "certs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    app_name: str = "szymon"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 2137
    frontend_url: str = "http://localhost:5173"

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


def _init_google_auth() -> Optional[GoogleAuthService]:
    """Initialize shared Google OAuth service if configured."""
    if not settings.google_client_id or not settings.google_client_secret:
        return None
    redirect_uri = f"https://localhost:{settings.port}/api/tasks/auth/callback"
    return GoogleAuthService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_path=settings.google_token_path,
        redirect_uri=redirect_uri,
    )


def _init_google_tasks(auth: Optional[GoogleAuthService]) -> Optional[GoogleTasksService]:
    """Initialize Google Tasks service if auth is configured."""
    if auth is None:
        return None
    return GoogleTasksService(auth_service=auth)


def _init_google_calendar(auth: Optional[GoogleAuthService]) -> Optional[GoogleCalendarService]:
    """Initialize Google Calendar service if auth is configured."""
    if auth is None:
        return None
    return GoogleCalendarService(auth_service=auth)


# Initialize services and routers
_google_auth = _init_google_auth()
tasks_router.init_service(_init_google_tasks(_google_auth), settings.frontend_url)
calendar_router.init_service(_init_google_calendar(_google_auth), settings.frontend_url)


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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions to prevent app crashes."""
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# Include routers
app.include_router(tasks_router.router)
app.include_router(calendar_router.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ASSETS_DIR / "favicon.gif", media_type="image/gif")


@app.get("/health")
def health():
    return {"status": "ok"}


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
