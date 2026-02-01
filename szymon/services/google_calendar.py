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
