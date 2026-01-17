import socket
import subprocess
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
CERTS_DIR = ROOT_DIR / "certs"
WEB_DIR = ROOT_DIR / "web" / "dist"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_name: str = "szymon"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 2137

    @property
    def ssl_certfile(self) -> Path:
        return CERTS_DIR / "cert.pem"

    @property
    def ssl_keyfile(self) -> Path:
        return CERTS_DIR / "key.pem"


settings = Settings()


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
