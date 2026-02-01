---
date: 2026-02-01T14:51:37Z
researcher: Claude
git_commit: fa55d4a596481fdb2953da905a22ffb47c60c2ce
branch: main
repository: szymon
topic: "Google Calendar API Integration for Szymon App"
tags: [research, codebase, google-calendar, oauth, fastapi, frontend]
status: complete
last_updated: 2026-02-01
last_updated_by: Claude
---

# Research: Google Calendar API Integration for Szymon App

**Date**: 2026-02-01T14:51:37Z
**Researcher**: Claude
**Git Commit**: fa55d4a596481fdb2953da905a22ffb47c60c2ce
**Branch**: main
**Repository**: szymon

## Research Question

How to integrate Google Calendar service with the Szymon app to collect all events from the calendar, display them on a different page, and allow modifications from the app.

## Summary

The Szymon app already has a well-structured Google Tasks integration that provides an excellent template for adding Google Calendar support. The integration follows a clean service-router pattern with OAuth 2.0 authentication. Adding Calendar support involves:

1. **Creating a new service** (`google_calendar.py`) following the existing `google_tasks.py` pattern
2. **Creating a new router** (`calendar.py`) following the existing `tasks.py` pattern
3. **Wiring up in main.py** with a shared or separate token file
4. **Extending the frontend** to add a calendar page/view

The same OAuth client credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) can be reused, and tokens can be shared if scopes are combined.

## Detailed Findings

### Existing Architecture

The app follows a clean layered architecture:

```
szymon/
  main.py              # FastAPI app, settings, service initialization
  routers/
    __init__.py
    tasks.py           # API endpoints with init_service() pattern
  services/
    __init__.py
    google_tasks.py    # Business logic + OAuth + Pydantic models
```

**Key patterns from existing implementation:**

| Pattern | Location | Purpose |
|---------|----------|---------|
| Service Layer | `services/google_tasks.py` | Encapsulates all Google API logic |
| Router with DI | `routers/tasks.py` | Module-level service injection via `init_service()` |
| Settings via pydantic-settings | `main.py:21-44` | Type-safe config from `.env` |
| Lazy API client | `google_tasks.py:89-94` | Creates Google API service on first use |
| OAuth flow | `google_tasks.py:51-114` | Complete auth URL, exchange, refresh logic |

### Google Calendar API Details

#### OAuth Scopes

| Scope | URL | Use Case |
|-------|-----|----------|
| Events read/write | `https://www.googleapis.com/auth/calendar.events` | **Recommended** - view and edit events |
| Events read-only | `https://www.googleapis.com/auth/calendar.events.readonly` | View-only access |
| Full calendar | `https://www.googleapis.com/auth/calendar` | Also manage calendars themselves |

**Recommendation**: Use `calendar.events` scope for principle of least privilege.

#### Key API Methods

```python
service = build("calendar", "v3", credentials=creds)

# List events
service.events().list(
    calendarId="primary",
    timeMin="2026-02-01T00:00:00Z",
    timeMax="2026-02-08T00:00:00Z",
    singleEvents=True,  # Expand recurring events
    orderBy="startTime"
)

# Create event
service.events().insert(calendarId="primary", body=event_data)

# Update event
service.events().update(calendarId="primary", eventId="...", body=event_data)

# Delete event
service.events().delete(calendarId="primary", eventId="...")

# Quick add (natural language)
service.events().quickAdd(calendarId="primary", text="Meeting tomorrow at 3pm")
```

#### Event Data Structure

```python
{
    "id": "abc123",
    "summary": "Event Title",
    "description": "Details",
    "location": "123 Main St",
    "start": {
        "dateTime": "2026-02-01T09:00:00-05:00",
        "timeZone": "America/New_York"
    },
    "end": {
        "dateTime": "2026-02-01T10:00:00-05:00",
        "timeZone": "America/New_York"
    },
    "status": "confirmed",  # or "tentative", "cancelled"
    "attendees": [{"email": "...", "responseStatus": "accepted"}],
    "reminders": {"useDefault": False, "overrides": [...]},
    "htmlLink": "https://www.google.com/calendar/event?eid=...",
    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
    "conferenceData": {...}  # Google Meet info
}
```

### Tasks vs Calendar API Comparison

| Aspect | Tasks API | Calendar API |
|--------|-----------|--------------|
| Service name | `build("tasks", "v1", ...)` | `build("calendar", "v3", ...)` |
| Time support | **Date only** (no time!) | Full datetime with timezone |
| Recurrence | Not supported | Full RRULE support |
| Attendees | Not supported | Full support |
| Location | Not supported | Supported |
| Reminders | Not supported | Multiple types |

**Critical**: Google Tasks API discards time from the `due` field - only the date is stored.

### Implementation Plan

#### 1. Create Service (`szymon/services/google_calendar.py`)

```python
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

class EventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: str  # ISO format
    end_datetime: str
    timezone: str = "UTC"

class EventUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None

class GoogleCalendarService:
    def __init__(self, client_id, client_secret, token_path, redirect_uri):
        # Same pattern as GoogleTasksService

    def list_events(self, calendar_id="primary", time_min=None, time_max=None):
        ...

    def get_event(self, event_id, calendar_id="primary"):
        ...

    def create_event(self, event: EventCreate, calendar_id="primary"):
        ...

    def update_event(self, event_id, event: EventUpdate, calendar_id="primary"):
        ...

    def delete_event(self, event_id, calendar_id="primary"):
        ...
```

#### 2. Create Router (`szymon/routers/calendar.py`)

```python
router = APIRouter(prefix="/api/calendar", tags=["calendar"])

_service: Optional[GoogleCalendarService] = None

def init_service(service): ...
def _require_service(): ...

@router.get("/auth/status")
@router.get("/auth/login")
@router.get("/auth/callback")
@router.get("/calendars")  # List calendars
@router.get("")  # List events (with time_min, time_max params)
@router.get("/{event_id}")
@router.post("")
@router.put("/{event_id}")
@router.delete("/{event_id}")
```

#### 3. Wire Up in `main.py`

```python
from szymon.routers import calendar as calendar_router
from szymon.services.google_calendar import GoogleCalendarService

# Add token path for calendar
@property
def google_calendar_token_path(self) -> Path:
    return ROOT_DIR / ".google_calendar_token.json"

def _init_google_calendar() -> Optional[GoogleCalendarService]:
    if not settings.google_client_id or not settings.google_client_secret:
        return None
    redirect_uri = f"https://localhost:{settings.port}/api/calendar/auth/callback"
    return GoogleCalendarService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_path=settings.google_calendar_token_path,
        redirect_uri=redirect_uri,
    )

calendar_router.init_service(_init_google_calendar())
app.include_router(calendar_router.router)
```

#### 4. Frontend Options

**Option A: Add calendar view to existing App.jsx**
- Add tabs/navigation to switch between Tasks and Calendar views
- Reuse existing week navigation and column layout
- Events displayed with time information (unlike tasks)

**Option B: Create separate Calendar page**
- Add React Router for navigation
- Create `Calendar.jsx` component with its own auth check and data loading
- More separation of concerns

**Recommended Frontend Endpoints:**
```
GET /api/calendar/auth/status
GET /api/calendar/auth/login
GET /api/calendar (with ?time_min=...&time_max=... params)
POST /api/calendar
PUT /api/calendar/{event_id}
DELETE /api/calendar/{event_id}
```

### Unified OAuth Approach (Alternative)

Instead of separate token files, combine scopes for single auth flow:

```python
# In a shared auth service
COMBINED_SCOPES = [
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar.events",
]

# Single token file with both scopes
# User authorizes once, both services work
```

**Pros**: Single login for user, simpler UX
**Cons**: Must re-authenticate if adding new scopes later, more complex service architecture

## Code References

- `szymon/main.py:21-44` - Settings class with Google credentials
- `szymon/main.py:49-63` - Service initialization pattern
- `szymon/main.py:96-97` - Router registration
- `szymon/services/google_tasks.py:29-114` - OAuth flow implementation to replicate
- `szymon/services/google_tasks.py:130-199` - CRUD operations pattern
- `szymon/routers/tasks.py:10-30` - Router with service injection pattern
- `szymon/routers/tasks.py:32-59` - Auth endpoints pattern
- `web/src/App.jsx:266-311` - State management and week calculation
- `web/src/App.jsx:313-392` - API call patterns to replicate
- `web/src/App.jsx:446-576` - Calendar grid rendering

## Architecture Insights

1. **Service injection pattern**: Services are initialized at module load time in `main.py` and injected into routers via `init_service()`. This allows conditional initialization based on config.

2. **Lazy API client**: The Google API client (`self._service`) is created on first use, not at initialization. This prevents errors if credentials aren't available yet.

3. **Separate token files**: Current approach uses `.google_token.json`. For Calendar, use `.google_calendar_token.json` to allow independent auth.

4. **Frontend auth flow**: The frontend checks `/api/*/auth/status`, shows login link if not authenticated, then loads data. This pattern should be replicated for Calendar.

5. **Dependencies already installed**: `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib` are in `pyproject.toml`.

## Historical Context (from thoughts/)

- `thoughts/shared/plans/google-tasks-router-refactor.md` - Plan for refactoring Tasks into separate router (already implemented)
- `thoughts/shared/plans/minimal-calendar-design-system.md` - Design system for calendar UI (implemented in `App.jsx`)
- `thoughts/shared/research/2026-02-01_google-tasks-refactor.md` - Research on Tasks refactoring

## Open Questions

1. **Unified vs separate OAuth**: Should Calendar share the token with Tasks (requires re-auth with combined scopes) or use separate token?

2. **Calendar selection**: Should users be able to select which Google Calendar to view, or default to "primary"?

3. **Event editing UI**: What level of event editing is needed? Basic (title, time, description) or full (attendees, reminders, recurrence)?

4. **Integration with Tasks view**: Should Calendar events appear alongside Tasks in the weekly view, or be a completely separate page?

5. **All-day events**: How to handle all-day events (which use `date` instead of `dateTime`)?
