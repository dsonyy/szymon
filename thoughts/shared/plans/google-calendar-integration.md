# Google Calendar Integration Implementation Plan

## Overview

Add Google Calendar API integration to the Szymon app, enabling users to view and manage calendar events on a separate page with a weekly view. This follows the existing Google Tasks pattern and uses a unified OAuth token with combined scopes.

## Current State Analysis

The app has a working Google Tasks integration that provides an excellent template:

- **Service**: `szymon/services/google_tasks.py` - OAuth flow, lazy API client, CRUD operations
- **Router**: `szymon/routers/tasks.py` - Module-level service injection, auth endpoints, REST API
- **Main**: `szymon/main.py` - Settings, service initialization, router registration
- **Frontend**: `web/src/App.jsx` - Week view with auth checking, API calls, task grouping

### Key Discoveries:
- OAuth credentials and token stored in Settings class (`main.py:29-43`)
- Service injection pattern via `init_service()` function (`tasks.py:16-19`)
- Lazy Google API client creation (`google_tasks.py:89-94`)
- Frontend handles three auth states: not configured, not authenticated, authenticated (`App.jsx:391-407`)

## Desired End State

1. **Unified OAuth**: Single token file (`.google_token.json`) with both Tasks and Calendar scopes
2. **Calendar Service**: `szymon/services/google_calendar.py` with OAuth integration and CRUD operations
3. **Calendar Router**: `szymon/routers/calendar.py` with REST API endpoints
4. **Shared Auth Module**: `szymon/services/google_auth.py` for common OAuth logic
5. **Frontend**: Navigation between Tasks and Calendar views, Calendar page component

### Verification:
- Server starts without errors
- `/api/calendar/auth/status` returns `{configured, authenticated}`
- After OAuth login, both Tasks and Calendar endpoints work
- Calendar events displayed in week view
- Event CRUD operations functional

## What We're NOT Doing

- Attendee management (out of scope for basic editing)
- Reminder configuration (use Google Calendar defaults)
- Recurring event editing (can view but not create)
- Drag-and-drop rescheduling
- Month or day views (week view only)
- Event color customization

## Implementation Approach

The implementation requires careful sequencing due to the unified OAuth change:

1. **Phase 1**: Extract shared OAuth logic and update Tasks to use it
2. **Phase 2**: Add Calendar service and router
3. **Phase 3**: Update frontend with navigation and Calendar page

## Phase 1: Shared OAuth Module

### Overview
Extract OAuth logic from `google_tasks.py` into a shared module. Update Tasks service to use it. Add Calendar scope to the unified scope list. This phase ensures existing functionality keeps working while preparing for Calendar.

### Changes Required:

#### 1. Create Shared Auth Module
**File**: `szymon/services/google_auth.py` (new file)
**Purpose**: Common OAuth credentials management for all Google services

```python
"""Shared Google OAuth authentication module."""

from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

# Combined scopes for all Google services
SCOPES = [
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleAuthService:
    """Shared OAuth service for Google APIs."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_path: Path,
        redirect_uri: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = token_path
        self.redirect_uri = redirect_uri

    def _get_client_config(self) -> dict:
        """Get OAuth client configuration."""
        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }

    def _get_flow(self) -> Flow:
        """Create OAuth flow."""
        return Flow.from_client_config(
            self._get_client_config(),
            scopes=SCOPES,
            redirect_uri=self.redirect_uri,
        )

    def get_credentials(self) -> Credentials:
        """Get or refresh OAuth2 credentials."""
        creds = None

        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self._save_credentials(creds)
            else:
                raise Exception("Not authenticated. Visit /api/auth/login to authenticate.")

        return creds

    def _save_credentials(self, creds: Credentials):
        """Save credentials to token file."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w") as token:
            token.write(creds.to_json())

    def exchange_code(self, code: str) -> Credentials:
        """Exchange authorization code for credentials."""
        flow = self._get_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        self._save_credentials(creds)
        return creds

    def is_authenticated(self) -> bool:
        """Check if valid credentials exist."""
        if not self.token_path.exists():
            return False
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            return creds.valid or (creds.expired and creds.refresh_token)
        except Exception:
            return False

    def get_auth_url(self) -> tuple[str, str]:
        """Get the OAuth authorization URL. Returns (url, state)."""
        flow = self._get_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url, state
```

#### 2. Update Google Tasks Service
**File**: `szymon/services/google_tasks.py`
**Changes**: Remove OAuth logic, use shared auth service

```python
"""Google Tasks API service with CRUD operations."""

from typing import Optional

from googleapiclient.discovery import build
from pydantic import BaseModel

from szymon.services.google_auth import GoogleAuthService


class TaskCreate(BaseModel):
    title: str
    notes: Optional[str] = None
    due: Optional[str] = None  # RFC 3339 timestamp


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    due: Optional[str] = None
    status: Optional[str] = None  # "needsAction" or "completed"


class GoogleTasksService:
    """Service for interacting with Google Tasks API."""

    def __init__(self, auth_service: GoogleAuthService):
        self.auth = auth_service
        self._service = None

    def _get_service(self):
        """Get or create the Tasks API service."""
        if self._service is None:
            creds = self.auth.get_credentials()
            self._service = build("tasks", "v1", credentials=creds)
        return self._service

    def is_authenticated(self) -> bool:
        """Check if valid credentials exist."""
        return self.auth.is_authenticated()

    def get_auth_url(self) -> tuple[str, str]:
        """Get the OAuth authorization URL."""
        return self.auth.get_auth_url()

    def exchange_code(self, code: str):
        """Exchange authorization code for credentials."""
        return self.auth.exchange_code(code)

    # Task Lists

    def list_task_lists(self, max_results: int = 100) -> list[dict]:
        """List all task lists."""
        service = self._get_service()
        results = service.tasklists().list(maxResults=max_results).execute()
        return results.get("items", [])

    def get_default_task_list_id(self) -> str:
        """Get the ID of the default task list (@default)."""
        return "@default"

    # Tasks CRUD

    def list_tasks(
        self,
        task_list_id: str = "@default",
        max_results: int = 100,
        show_completed: bool = True,
        show_hidden: bool = True,
    ) -> list[dict]:
        """List all tasks in a task list."""
        service = self._get_service()
        results = (
            service.tasks()
            .list(
                tasklist=task_list_id,
                maxResults=max_results,
                showCompleted=show_completed,
                showHidden=show_hidden,
            )
            .execute()
        )
        return results.get("items", [])

    def get_task(self, task_id: str, task_list_id: str = "@default") -> dict:
        """Get a specific task by ID."""
        service = self._get_service()
        return service.tasks().get(tasklist=task_list_id, task=task_id).execute()

    def create_task(self, task: TaskCreate, task_list_id: str = "@default") -> dict:
        """Create a new task."""
        service = self._get_service()
        body = {"title": task.title}
        if task.notes:
            body["notes"] = task.notes
        if task.due:
            body["due"] = task.due
        return service.tasks().insert(tasklist=task_list_id, body=body).execute()

    def update_task(
        self, task_id: str, task: TaskUpdate, task_list_id: str = "@default"
    ) -> dict:
        """Update an existing task."""
        service = self._get_service()
        existing = self.get_task(task_id, task_list_id)

        if task.title is not None:
            existing["title"] = task.title
        if task.notes is not None:
            existing["notes"] = task.notes
        if task.due is not None:
            existing["due"] = task.due
        if task.status is not None:
            existing["status"] = task.status

        return (
            service.tasks()
            .update(tasklist=task_list_id, task=task_id, body=existing)
            .execute()
        )

    def delete_task(self, task_id: str, task_list_id: str = "@default") -> None:
        """Delete a task."""
        service = self._get_service()
        service.tasks().delete(tasklist=task_list_id, task=task_id).execute()

    def complete_task(self, task_id: str, task_list_id: str = "@default") -> dict:
        """Mark a task as completed."""
        return self.update_task(task_id, TaskUpdate(status="completed"), task_list_id)

    def uncomplete_task(self, task_id: str, task_list_id: str = "@default") -> dict:
        """Mark a task as not completed."""
        return self.update_task(task_id, TaskUpdate(status="needsAction"), task_list_id)
```

#### 3. Update main.py Service Initialization
**File**: `szymon/main.py`
**Changes**: Create shared auth service, pass to Tasks service

Replace lines 49-59:

```python
from szymon.services.google_auth import GoogleAuthService


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


# Initialize services and routers
_google_auth = _init_google_auth()
tasks_router.init_service(_init_google_tasks(_google_auth))
```

### Success Criteria:

#### Automated Verification:
- [x] Server starts: `python -m szymon.main`
- [x] No import errors
- [x] Health endpoint works: `curl -k https://localhost:2137/health`

#### Manual Verification:
- [ ] Existing Tasks functionality still works after refactor
- [ ] OAuth login redirects correctly
- [ ] Tasks CRUD operations functional
- [ ] Delete existing `.google_token.json` and re-authenticate to get new token with combined scopes

---

## Phase 2: Calendar Service and Router

### Overview
Add the Calendar service and router following the Tasks pattern. Both services share the same auth service and token.

### Changes Required:

#### 1. Create Calendar Service
**File**: `szymon/services/google_calendar.py` (new file)

```python
"""Google Calendar API service with CRUD operations."""

from datetime import datetime, timedelta
from typing import Optional

from googleapiclient.discovery import build
from pydantic import BaseModel

from szymon.services.google_auth import GoogleAuthService


class EventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: str  # ISO 8601 format
    end_datetime: str  # ISO 8601 format
    timezone: str = "UTC"


class EventUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    timezone: Optional[str] = None


class GoogleCalendarService:
    """Service for interacting with Google Calendar API."""

    def __init__(self, auth_service: GoogleAuthService):
        self.auth = auth_service
        self._service = None

    def _get_service(self):
        """Get or create the Calendar API service."""
        if self._service is None:
            creds = self.auth.get_credentials()
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def is_authenticated(self) -> bool:
        """Check if valid credentials exist."""
        return self.auth.is_authenticated()

    def get_auth_url(self) -> tuple[str, str]:
        """Get the OAuth authorization URL."""
        return self.auth.get_auth_url()

    def exchange_code(self, code: str):
        """Exchange authorization code for credentials."""
        return self.auth.exchange_code(code)

    # Calendars

    def list_calendars(self) -> list[dict]:
        """List all calendars the user has access to."""
        service = self._get_service()
        results = service.calendarList().list().execute()
        return results.get("items", [])

    # Events CRUD

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 250,
    ) -> list[dict]:
        """List events in a calendar within the given time range."""
        service = self._get_service()

        # Default to current week if no time range specified
        if time_min is None:
            now = datetime.utcnow()
            time_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
        if time_max is None:
            now = datetime.utcnow()
            week_end = now + timedelta(days=7)
            time_max = week_end.replace(hour=23, minute=59, second=59, microsecond=0).isoformat() + "Z"

        results = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,  # Expand recurring events
                orderBy="startTime",
            )
            .execute()
        )
        return results.get("items", [])

    def get_event(self, event_id: str, calendar_id: str = "primary") -> dict:
        """Get a specific event by ID."""
        service = self._get_service()
        return service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    def create_event(self, event: EventCreate, calendar_id: str = "primary") -> dict:
        """Create a new event."""
        service = self._get_service()
        body = {
            "summary": event.summary,
            "start": {
                "dateTime": event.start_datetime,
                "timeZone": event.timezone,
            },
            "end": {
                "dateTime": event.end_datetime,
                "timeZone": event.timezone,
            },
        }
        if event.description:
            body["description"] = event.description
        if event.location:
            body["location"] = event.location

        return service.events().insert(calendarId=calendar_id, body=body).execute()

    def update_event(
        self, event_id: str, event: EventUpdate, calendar_id: str = "primary"
    ) -> dict:
        """Update an existing event."""
        service = self._get_service()
        existing = self.get_event(event_id, calendar_id)

        if event.summary is not None:
            existing["summary"] = event.summary
        if event.description is not None:
            existing["description"] = event.description
        if event.location is not None:
            existing["location"] = event.location
        if event.start_datetime is not None:
            existing["start"] = {
                "dateTime": event.start_datetime,
                "timeZone": event.timezone or existing.get("start", {}).get("timeZone", "UTC"),
            }
        if event.end_datetime is not None:
            existing["end"] = {
                "dateTime": event.end_datetime,
                "timeZone": event.timezone or existing.get("end", {}).get("timeZone", "UTC"),
            }

        return (
            service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=existing)
            .execute()
        )

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        """Delete an event."""
        service = self._get_service()
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

    def quick_add(self, text: str, calendar_id: str = "primary") -> dict:
        """Create an event using natural language (e.g., 'Meeting tomorrow at 3pm')."""
        service = self._get_service()
        return service.events().quickAdd(calendarId=calendar_id, text=text).execute()
```

#### 2. Create Calendar Router
**File**: `szymon/routers/calendar.py` (new file)

```python
"""Google Calendar API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from szymon.services.google_calendar import GoogleCalendarService, EventCreate, EventUpdate

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

# Service instance (initialized from main.py)
_service: Optional[GoogleCalendarService] = None


def init_service(service: Optional[GoogleCalendarService]) -> None:
    """Initialize the Google Calendar service. Called from main.py."""
    global _service
    _service = service


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
        return RedirectResponse(url="/calendar")
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
```

#### 3. Update main.py to Include Calendar
**File**: `szymon/main.py`
**Changes**: Add Calendar service initialization and router registration

Add imports:
```python
from szymon.routers import calendar as calendar_router
from szymon.services.google_calendar import GoogleCalendarService
```

Add initialization function:
```python
def _init_google_calendar(auth: Optional[GoogleAuthService]) -> Optional[GoogleCalendarService]:
    """Initialize Google Calendar service if auth is configured."""
    if auth is None:
        return None
    return GoogleCalendarService(auth_service=auth)
```

Update service initialization:
```python
# Initialize services and routers
_google_auth = _init_google_auth()
tasks_router.init_service(_init_google_tasks(_google_auth))
calendar_router.init_service(_init_google_calendar(_google_auth))
```

Add router registration (after `app.include_router(tasks_router.router)`):
```python
app.include_router(calendar_router.router)
```

### Success Criteria:

#### Automated Verification:
- [x] Server starts without errors: `python -m szymon.main`
- [x] Calendar auth status: `curl -k https://localhost:2137/api/calendar/auth/status`
- [ ] Calendar list (after auth): `curl -k https://localhost:2137/api/calendar/calendars`
- [ ] Events list: `curl -k https://localhost:2137/api/calendar/events`

#### Manual Verification:
- [ ] OAuth login via `/api/calendar/auth/login` works
- [ ] After login, both Tasks and Calendar endpoints work (unified token)
- [ ] Can create an event via POST to `/api/calendar/events`
- [ ] Can view event details
- [ ] Can update and delete events
- [ ] Calendar picker returns list of user's calendars

---

## Phase 3: Frontend Calendar View

### Overview
Add navigation tabs to switch between Tasks and Calendar views. Create a new Calendar component with week view, calendar selector, and event display.

### Changes Required:

#### 1. Add React Router
**File**: `web/package.json`
**Changes**: Add react-router-dom dependency

```bash
cd web && npm install react-router-dom
```

#### 2. Create Calendar Component
**File**: `web/src/Calendar.jsx` (new file)

```jsx
import { useState, useEffect, useMemo } from "react";

// Reuse design system and styles from App.jsx
const designSystem = {
  fonts: {
    calendar: "'Times New Roman', Times, serif",
    tasks: "'Courier New', Courier, monospace",
    ui: "system-ui, -apple-system, sans-serif"
  },
  colors: {
    text: "#1a1a1a",
    textMuted: "#666",
    textLight: "#999",
    border: "#e0e0e0",
    borderLight: "#f0f0f0",
    background: "#fff",
    backgroundHover: "#fafafa",
    backgroundToday: "#fffbeb",
    accent: "#333",
    completed: "#999"
  },
  spacing: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem"
  }
};

// Date utilities
const getWeekStart = (date) => {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  d.setHours(0, 0, 0, 0);
  return d;
};

const getWeekDays = (weekStart) => {
  return Array.from({ length: 7 }, (_, i) => {
    const date = new Date(weekStart);
    date.setDate(date.getDate() + i);
    return date;
  });
};

const isSameDay = (d1, d2) => {
  return d1.toDateString() === d2.toDateString();
};

const formatTime = (dateTimeStr) => {
  const date = new Date(dateTimeStr);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
};

const groupEventsByDate = (events, weekDays) => {
  const groups = Object.fromEntries(weekDays.map(d => [d.toDateString(), []]));

  events.forEach(event => {
    // Handle all-day events (have date) vs timed events (have dateTime)
    const startStr = event.start?.dateTime || event.start?.date;
    if (!startStr) return;

    const startDate = new Date(startStr);
    startDate.setHours(0, 0, 0, 0);
    const dateKey = startDate.toDateString();

    if (groups[dateKey] !== undefined) {
      groups[dateKey].push(event);
    }
  });

  // Sort events by start time within each day
  Object.keys(groups).forEach(key => {
    groups[key].sort((a, b) => {
      const aTime = new Date(a.start?.dateTime || a.start?.date);
      const bTime = new Date(b.start?.dateTime || b.start?.date);
      return aTime - bTime;
    });
  });

  return groups;
};

const styles = {
  // ... (same styles as App.jsx with event-specific additions)
  eventItem: {
    fontFamily: designSystem.fonts.tasks,
    fontSize: "0.8125rem",
    padding: designSystem.spacing.sm,
    borderBottom: `1px solid ${designSystem.colors.borderLight}`,
    cursor: "pointer",
  },
  eventTime: {
    fontSize: "0.75rem",
    color: designSystem.colors.textMuted,
    marginBottom: "2px",
  },
  eventTitle: {
    wordBreak: "break-word",
  },
  eventLocation: {
    fontSize: "0.75rem",
    color: designSystem.colors.textMuted,
    marginTop: "2px",
  },
  calendarSelector: {
    padding: designSystem.spacing.sm,
    border: `1px solid ${designSystem.colors.border}`,
    borderRadius: "4px",
    fontFamily: designSystem.fonts.ui,
    fontSize: "0.875rem",
    backgroundColor: designSystem.colors.background,
  },
  // Copy other styles from App.jsx...
};

export default function Calendar() {
  const [authStatus, setAuthStatus] = useState(null);
  const [events, setEvents] = useState([]);
  const [calendars, setCalendars] = useState([]);
  const [selectedCalendar, setSelectedCalendar] = useState("primary");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weekOffset, setWeekOffset] = useState(0);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // Mobile detection
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Calculate week
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const weekStart = useMemo(() => {
    const start = getWeekStart(new Date());
    start.setDate(start.getDate() + weekOffset * 7);
    return start;
  }, [weekOffset]);

  const weekEnd = useMemo(() => {
    const end = new Date(weekStart);
    end.setDate(end.getDate() + 7);
    return end;
  }, [weekStart]);

  const weekDays = useMemo(() => getWeekDays(weekStart), [weekStart]);

  const groupedEvents = useMemo(
    () => groupEventsByDate(events, weekDays),
    [events, weekDays]
  );

  const checkAuthAndLoad = async () => {
    try {
      const authRes = await fetch("/api/calendar/auth/status");
      const auth = await authRes.json();
      setAuthStatus(auth);

      if (auth.configured && auth.authenticated) {
        await loadCalendars();
        await loadEvents();
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadCalendars = async () => {
    try {
      const res = await fetch("/api/calendar/calendars");
      if (!res.ok) throw new Error("Failed to load calendars");
      const data = await res.json();
      setCalendars(data);
    } catch (e) {
      console.error("Failed to load calendars:", e);
    }
  };

  const loadEvents = async () => {
    try {
      const timeMin = weekStart.toISOString();
      const timeMax = weekEnd.toISOString();
      const res = await fetch(
        `/api/calendar/events?calendar_id=${selectedCalendar}&time_min=${timeMin}&time_max=${timeMax}`
      );
      if (!res.ok) throw new Error("Failed to load events");
      const data = await res.json();
      setEvents(data);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    checkAuthAndLoad();
  }, []);

  useEffect(() => {
    if (authStatus?.authenticated) {
      loadEvents();
    }
  }, [weekOffset, selectedCalendar]);

  const deleteEvent = async (eventId) => {
    if (!confirm("Delete this event?")) return;
    try {
      const res = await fetch(`/api/calendar/events/${eventId}?calendar_id=${selectedCalendar}`, {
        method: "DELETE"
      });
      if (!res.ok) throw new Error("Failed to delete event");
      await loadEvents();
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) {
    return <div style={styles.loading}>Loading...</div>;
  }

  if (!authStatus?.configured) {
    return (
      <div style={styles.authMessage}>
        <p>Google Calendar not configured.</p>
        <p>Set <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> in <code>.env</code></p>
      </div>
    );
  }

  if (!authStatus?.authenticated) {
    return (
      <div style={styles.authMessage}>
        <p>Not authenticated with Google Calendar.</p>
        <a href="/api/calendar/auth/login" style={styles.authLink}>
          Login with Google
        </a>
      </div>
    );
  }

  return (
    <>
      {error && <div style={styles.error}>{error}</div>}

      {/* Navigation */}
      <div style={styles.navigation}>
        <button style={styles.navButton} onClick={() => setWeekOffset(w => w - 1)}>
          ← Prev
        </button>
        <span style={styles.weekLabel}>
          {weekStart.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
        </span>
        <button style={styles.navButton} onClick={() => setWeekOffset(w => w + 1)}>
          Next →
        </button>
        {weekOffset !== 0 && (
          <button style={styles.navButton} onClick={() => setWeekOffset(0)}>
            Today
          </button>
        )}
        <button style={styles.navButton} onClick={loadEvents}>
          ↻
        </button>

        {/* Calendar selector */}
        <select
          style={styles.calendarSelector}
          value={selectedCalendar}
          onChange={(e) => setSelectedCalendar(e.target.value)}
        >
          {calendars.map(cal => (
            <option key={cal.id} value={cal.id}>
              {cal.summary}
            </option>
          ))}
        </select>
      </div>

      {/* Week Grid */}
      <div style={isMobile ? styles.mobileContainer : styles.calendarContainer}>
        {weekDays.map((day) => {
          const dateKey = day.toDateString();
          const isToday = isSameDay(day, today);
          const dayEvents = groupedEvents[dateKey] || [];

          return (
            <div
              key={dateKey}
              style={{
                ...styles.column,
                ...(isToday ? styles.columnToday : {}),
                ...(isMobile ? styles.mobileColumn : {}),
              }}
            >
              <div style={styles.dayHeader}>
                <div style={styles.dayNumber}>{day.getDate()}</div>
                <div style={styles.dayName}>
                  {day.toLocaleDateString('en-US', { weekday: 'short' })}
                </div>
              </div>

              <div style={styles.taskList}>
                {dayEvents.map((event) => (
                  <div key={event.id} style={styles.eventItem}>
                    {event.start?.dateTime && (
                      <div style={styles.eventTime}>
                        {formatTime(event.start.dateTime)}
                        {event.end?.dateTime && ` - ${formatTime(event.end.dateTime)}`}
                      </div>
                    )}
                    <div style={styles.eventTitle}>{event.summary}</div>
                    {event.location && (
                      <div style={styles.eventLocation}>📍 {event.location}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
```

#### 3. Update App.jsx with Navigation
**File**: `web/src/App.jsx`
**Changes**: Add tabs for Tasks/Calendar navigation

Add at the top of the authenticated section (after auth checks, before week navigation):

```jsx
{/* View Navigation Tabs */}
<div style={styles.viewTabs}>
  <a
    href="/"
    style={{
      ...styles.viewTab,
      ...(location.pathname === "/" ? styles.viewTabActive : {}),
    }}
  >
    Tasks
  </a>
  <a
    href="/calendar"
    style={{
      ...styles.viewTab,
      ...(location.pathname === "/calendar" ? styles.viewTabActive : {}),
    }}
  >
    Calendar
  </a>
</div>
```

Add styles:
```javascript
viewTabs: {
  display: "flex",
  gap: designSystem.spacing.xs,
  padding: designSystem.spacing.md,
  borderBottom: `1px solid ${designSystem.colors.border}`,
},
viewTab: {
  padding: `${designSystem.spacing.sm} ${designSystem.spacing.md}`,
  textDecoration: "none",
  color: designSystem.colors.textMuted,
  borderRadius: "4px",
},
viewTabActive: {
  backgroundColor: designSystem.colors.backgroundToday,
  color: designSystem.colors.text,
  fontWeight: "500",
},
```

#### 4. Update main.jsx with Router
**File**: `web/src/main.jsx`

```jsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App.jsx";
import Calendar from "./Calendar.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/calendar" element={<Calendar />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
```

#### 5. Create Shared Layout Component (Optional Enhancement)
**File**: `web/src/Layout.jsx` (new file)

```jsx
import { useLocation } from "react-router-dom";

// Extract shared styles and design system to a separate file
// This is optional but reduces code duplication

export default function Layout({ children, health }) {
  const location = useLocation();

  return (
    <div style={styles.app}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>Szymon</h1>
        <span>{health?.status === "ok" ? "●" : "○"} API</span>
      </div>

      {/* View Navigation */}
      <div style={styles.viewTabs}>
        <a
          href="/"
          style={{
            ...styles.viewTab,
            ...(location.pathname === "/" ? styles.viewTabActive : {}),
          }}
        >
          Tasks
        </a>
        <a
          href="/calendar"
          style={{
            ...styles.viewTab,
            ...(location.pathname === "/calendar" ? styles.viewTabActive : {}),
          }}
        >
          Calendar
        </a>
      </div>

      {children}
    </div>
  );
}
```

### Success Criteria:

#### Automated Verification:
- [x] Frontend builds: `cd web && npm run build`
- [ ] No console errors in browser

#### Manual Verification:
- [ ] Navigation tabs visible (Tasks / Calendar)
- [ ] Clicking Calendar tab navigates to `/calendar`
- [ ] Calendar view shows week grid
- [ ] Calendar selector dropdown lists user's calendars
- [ ] Events appear in correct day columns
- [ ] Event times displayed correctly
- [ ] Week navigation works (Prev/Next/Today)
- [ ] Mobile view shows stacked columns

---

## Testing Strategy

### Unit Tests:
- GoogleAuthService: token storage, refresh, scope validation
- GoogleCalendarService: event creation, date handling
- Router endpoints: auth status, CRUD operations

### Integration Tests:
- Full OAuth flow with combined scopes
- Tasks and Calendar working with shared token
- Event CRUD lifecycle

### Manual Testing Steps:
1. Delete existing `.google_token.json`
2. Start server, visit Tasks page
3. Click login - should request both Tasks and Calendar scopes
4. After auth, verify Tasks functionality works
5. Navigate to Calendar view
6. Verify Calendar shows events without re-auth
7. Test calendar picker - select different calendar
8. Verify week navigation
9. Create event via API, verify it appears
10. Test on mobile viewport

## Migration Notes

**IMPORTANT: Users must re-authenticate after Phase 1**

The unified OAuth approach requires a token with combined scopes. Existing users with `.google_token.json` from Tasks-only will need to:

1. Delete `.google_token.json` from the repository root
2. Re-authenticate via `/api/tasks/auth/login` or `/api/calendar/auth/login`
3. Grant permissions for both Tasks and Calendar

Consider adding a check that detects old tokens and prompts re-authentication.

## Performance Considerations

- Event fetching limited to 250 events per week (configurable)
- Lazy API client creation prevents unnecessary connections
- Calendar list cached on frontend (refreshed on page load)

## References

- Research document: `thoughts/shared/research/2026-02-01_14-51-37_google-calendar-integration.md`
- Tasks service: `szymon/services/google_tasks.py`
- Tasks router: `szymon/routers/tasks.py`
- Frontend week view: `web/src/App.jsx`
- Design system plan: `thoughts/shared/plans/minimal-calendar-design-system.md`
