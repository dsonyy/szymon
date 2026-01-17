"""Google Tasks API service with CRUD operations."""

from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel

SCOPES = ["https://www.googleapis.com/auth/tasks"]


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

    def __init__(self, client_id: str, client_secret: str, token_path: Path, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = token_path
        self.redirect_uri = redirect_uri
        self._service = None

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

    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth2 credentials."""
        creds = None

        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self._save_credentials(creds)
            else:
                raise Exception("Not authenticated. Visit /api/tasks/auth/login to authenticate.")

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

    def _get_service(self):
        """Get or create the Tasks API service."""
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("tasks", "v1", credentials=creds)
        return self._service

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
        show_hidden: bool = False,
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
