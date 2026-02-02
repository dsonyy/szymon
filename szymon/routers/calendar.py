"""Google Calendar API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from szymon.services.google_calendar import GoogleCalendarService, EventCreate, EventUpdate

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

# Service instance (initialized from main.py)
_service: Optional[GoogleCalendarService] = None
_frontend_url: str = "http://localhost:5173"


def init_service(service: Optional[GoogleCalendarService], frontend_url: str = "http://localhost:5173") -> None:
    """Initialize the Google Calendar service. Called from main.py."""
    global _service, _frontend_url
    _service = service
    _frontend_url = frontend_url


def _require_service() -> GoogleCalendarService:
    """Helper to check if Google Calendar is configured."""
    if _service is None:
        raise HTTPException(
            status_code=503,
            detail="Google Calendar not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env",
        )
    return _service


@router.get("/auth/status")
def auth_status():
    """Check if Google Calendar is authenticated."""
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
        return RedirectResponse(url=f"{_frontend_url}/calendar")
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h1>Authentication failed</h1><p>{e}</p></body></html>",
            status_code=400,
        )


@router.get("/calendars")
def list_calendars():
    """List all calendars."""
    service = _require_service()
    try:
        return service.list_calendars()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
def list_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
):
    """List events in a calendar."""
    service = _require_service()
    try:
        return service.list_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{event_id}")
def get_event(event_id: str, calendar_id: str = "primary"):
    """Get a specific event."""
    service = _require_service()
    try:
        return service.get_event(event_id, calendar_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events")
def create_event(event: EventCreate, calendar_id: str = "primary"):
    """Create a new event."""
    service = _require_service()
    try:
        return service.create_event(event, calendar_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/quick")
def quick_add_event(text: str, calendar_id: str = "primary"):
    """Create an event using natural language."""
    service = _require_service()
    try:
        return service.quick_add(text, calendar_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/events/{event_id}")
def update_event(event_id: str, event: EventUpdate, calendar_id: str = "primary"):
    """Update an existing event."""
    service = _require_service()
    try:
        return service.update_event(event_id, event, calendar_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/events/{event_id}")
def delete_event(event_id: str, calendar_id: str = "primary"):
    """Delete an event."""
    service = _require_service()
    try:
        service.delete_event(event_id, calendar_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
