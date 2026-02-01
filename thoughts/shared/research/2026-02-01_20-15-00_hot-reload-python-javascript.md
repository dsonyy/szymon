---
date: 2026-02-01T20:15:00+01:00
researcher: Claude
git_commit: fa55d4a596481fdb2953da905a22ffb47c60c2ce
branch: main
repository: szymon
topic: "Hot reload for Python and JavaScript applications"
tags: [research, codebase, hot-reload, development, uvicorn, vite]
status: complete
last_updated: 2026-02-01
last_updated_by: Claude
---

# Research: Hot Reload for Python and JavaScript Applications

**Date**: 2026-02-01T20:15:00+01:00
**Researcher**: Claude
**Git Commit**: fa55d4a596481fdb2953da905a22ffb47c60c2ce
**Branch**: main
**Repository**: szymon

## Research Question
How to implement hot reload for Python and JavaScript applications in this codebase.

## Summary

This codebase already has hot reload configured for both Python (backend) and JavaScript (frontend):

- **Python/FastAPI**: Uses uvicorn's built-in `--reload` flag, enabled by default when `debug=True`
- **JavaScript/React**: Uses Vite's built-in HMR (Hot Module Replacement), available via `npm run dev`

Both can be run simultaneously for full-stack development with live reloading.

## Detailed Findings

### Python Hot Reload (uvicorn)

**Current Implementation**: Hot reload is already configured in `szymon/main.py:118-126`

```python
uvicorn.run(
    "szymon.main:app",       # App passed as string (required for reload)
    host=settings.host,
    port=settings.port,
    reload=settings.debug,   # Hot reload enabled when debug=True
    log_level="info",
    ssl_certfile=str(settings.ssl_certfile),
    ssl_keyfile=str(settings.ssl_keyfile),
)
```

**Key requirements for uvicorn reload to work:**
1. Pass app as import string `"module:app"` not direct reference
2. Set `reload=True` (controlled by `settings.debug` which defaults to `True`)

**How to run:**
```bash
# Option 1: Using the CLI entry point (recommended)
szymon

# Option 2: Using uvicorn directly with explicit reload
uvicorn szymon.main:app --reload

# Option 3: Using justfile
just run
```

**Configuration** (`szymon/main.py:21-27`):
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")
    debug: bool = True  # Controls hot reload
```

To disable hot reload, set `DEBUG=false` in `.env` file.

### JavaScript Hot Reload (Vite HMR)

**Current Implementation**: Vite provides HMR out of the box

**Configuration** (`web/vite.config.js`):
```javascript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
  },
});
```

The `@vitejs/plugin-react` plugin enables React Fast Refresh for component-level HMR.

**How to run** (`web/package.json:6-10`):
```bash
# Using npm
cd web && npm run dev

# Using justfile
just dev-web
```

**What Vite HMR provides:**
- Instant module replacement without full page reload
- React Fast Refresh preserves component state during updates
- CSS hot replacement
- Default dev server at `http://localhost:5173`

### Running Both Together (Full-Stack Development)

For full-stack development with hot reload on both backend and frontend:

**Terminal 1 - Backend:**
```bash
szymon
# or: just run
```

**Terminal 2 - Frontend:**
```bash
just dev-web
# or: cd web && npm run dev
```

**Note**: The production setup serves the built React app from `web/dist` via FastAPI's StaticFiles (`main.py:111-112`). During development, you'll have two servers:
- Backend API: `https://localhost:2137`
- Frontend dev: `http://localhost:5173`

### Adding Vite Proxy for API Calls (Optional Enhancement)

To avoid CORS issues during development, you could configure Vite to proxy API requests to the backend. Add to `web/vite.config.js`:

```javascript
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist" },
  server: {
    proxy: {
      '/api': {
        target: 'https://localhost:2137',
        changeOrigin: true,
        secure: false,  // Allow self-signed certs
      },
      '/health': {
        target: 'https://localhost:2137',
        changeOrigin: true,
        secure: false,
      }
    }
  }
});
```

## Code References

- `szymon/main.py:118-126` - uvicorn.run() with reload configuration
- `szymon/main.py:25` - debug setting that controls reload
- `szymon/main.py:119` - App passed as string for reload support
- `web/vite.config.js:1-9` - Vite configuration with React plugin
- `web/package.json:7` - dev script that runs Vite
- `justfile:19-21` - dev-web command for frontend hot reload
- `justfile:12-14` - run command for backend
- `pyproject.toml:8` - uvicorn[standard] dependency with reload support

## Architecture Insights

1. **Separation of concerns**: Backend (FastAPI/uvicorn) and frontend (Vite) have independent hot reload mechanisms
2. **Production vs Development**: In production, the React app is pre-built and served statically by FastAPI. In development, Vite's dev server provides HMR.
3. **SSL in development**: Backend uses HTTPS with auto-generated mkcert certificates. Frontend Vite server uses HTTP by default.

## Open Questions

1. Should a combined development command be added to justfile that starts both servers?
2. Should Vite be configured with a proxy to the backend API for seamless development?
3. Consider adding `watchfiles` to pyproject.toml for more efficient file watching on Linux.
