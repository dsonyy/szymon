"""Shared Google OAuth authentication module."""

from pathlib import Path

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
