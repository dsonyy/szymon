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
