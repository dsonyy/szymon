---
date: 2026-02-01T17:30:00+01:00
researcher: Claude
git_commit: fa55d4a596481fdb2953da905a22ffb47c60c2ce
branch: main
repository: szymon
topic: "Google Docs API Integration for Personal Assistant"
tags: [research, google-docs, google-api, llm-integration, rag, mcp]
status: complete
last_updated: 2026-02-01
last_updated_by: Claude
---

# Research: Google Docs API Integration for Personal Assistant

**Date**: 2026-02-01T17:30:00+01:00
**Researcher**: Claude
**Git Commit**: fa55d4a596481fdb2953da905a22ffb47c60c2ce
**Branch**: main
**Repository**: szymon

## Research Question

How can we integrate Google Docs into Szymon (personal assistant)? Can we create a separate service following existing patterns? What capabilities does the Google Docs API offer, and how can it be used efficiently with LLM integration for document management and workflows?

## Summary

Google Docs integration is highly feasible following the existing Google Tasks pattern in the codebase. The Google Docs API provides comprehensive read/write capabilities through the official `google-api-python-client` library (already a dependency). Key use cases include:

1. **Document reading** - Extract text for LLM processing, summaries, and RAG
2. **Document creation/editing** - LLM-generated content insertion, formatting
3. **RAG workflows** - Use documents as knowledge base with vector embeddings
4. **MCP integration** - Several community MCP servers exist for Claude/AI assistants

The existing OAuth pattern with `google-auth-oauthlib` can be reused with additional scopes for Docs.

## Detailed Findings

### 1. Existing Architecture Pattern

The codebase already has a working Google service integration pattern:

**Service Layer** (`szymon/services/google_tasks.py`):
- OAuth2 flow handling with `google_auth_oauthlib.flow.Flow`
- Credential management (load, refresh, save to JSON)
- Lazy service initialization via `_get_service()`
- CRUD operations wrapping the Google API client

**Router Layer** (`szymon/routers/tasks.py`):
- Module-level service singleton injected at startup
- Auth endpoints: `/auth/status`, `/auth/login`, `/auth/callback`
- Guard pattern with `_require_service()` for 503 responses

**Configuration** (`szymon/main.py`):
- Pydantic Settings with `google_client_id` and `google_client_secret`
- Factory function `_init_google_tasks()` for conditional initialization
- Token storage at `ROOT_DIR/.google_token.json`

### 2. Google Docs API Capabilities

#### Core Methods

| Method | Description |
|--------|-------------|
| `documents.create` | Create a new Google Document |
| `documents.get` | Retrieve document contents and metadata |
| `documents.batchUpdate` | Apply multiple atomic updates |

#### batchUpdate Operations (37 request types)

**Text Operations:**
- `InsertTextRequest` - Add text at a specified location
- `DeleteContentRangeRequest` - Remove content from a range
- `ReplaceAllTextRequest` - Find and replace throughout document

**Formatting:**
- `UpdateTextStyleRequest` - Modify bold, italic, font, etc.
- `UpdateParagraphStyleRequest` - Change paragraph formatting
- `UpdateDocumentStyleRequest` - Document-level styles

**Tables:**
- `InsertTableRequest`, `InsertTableRowRequest`, `InsertTableColumnRequest`
- `UpdateTableCellStyleRequest`, `MergeTableCellsRequest`

**Document Structure:**
- `InsertPageBreakRequest`, `InsertSectionBreakRequest`
- `CreateHeaderRequest`, `CreateFooterRequest`, `CreateFootnoteRequest`
- `InsertInlineImageRequest`

### 3. OAuth Scopes

| Scope | Description | Recommendation |
|-------|-------------|----------------|
| `documents` | Full read/write access | For full functionality |
| `documents.readonly` | Read-only access | For read-only use cases |
| `drive.file` | Per-file access (non-sensitive) | **Recommended** for minimal permissions |

The `drive.file` scope is non-sensitive and grants access only to files the app creates or users explicitly select.

### 4. Rate Limits

| Request Type | Per Minute/Project | Per Minute/User |
|--------------|-------------------|-----------------|
| Read | 3,000 | 300 |
| Write | 600 | 60 |

Exceeding limits returns HTTP 429. Implement exponential backoff for retry logic.

### 5. LLM Integration Patterns

#### A. Text Extraction for LLM Processing

Document structure is hierarchical: Document → Tabs → Body → StructuralElements → Paragraphs → TextRuns

```python
def extract_text(elements):
    text = ''
    for element in elements:
        if 'paragraph' in element:
            for elem in element['paragraph'].get('elements', []):
                text_run = elem.get('textRun')
                if text_run:
                    text += text_run.get('content', '')
        elif 'table' in element:
            for row in element['table'].get('tableRows', []):
                for cell in row.get('tableCells', []):
                    text += extract_text(cell.get('content', []))
    return text
```

#### B. RAG (Retrieval Augmented Generation)

**Option 1: Gemini File Search** (Recommended for 2026)
- Fully managed RAG by Google
- Automatic chunking, embedding, vector indexing
- Built-in citations
- $0.15/1M tokens for indexing (storage and queries free)

**Option 2: LangChain/LlamaIndex**
```python
from langchain_google_community import GoogleDriveLoader

loader = GoogleDriveLoader(
    document_ids=["doc_id_1", "doc_id_2"],
    credentials_path="credentials.json"
)
docs = loader.load()
```

**Option 3: Custom Pipeline**
1. Extract text via Google Docs API
2. Chunk text (semantic or fixed-size)
3. Generate embeddings (OpenAI, Cohere, local models)
4. Store in vector database (Pinecone, ChromaDB, pgvector)
5. Query and augment LLM prompts

#### C. LLM-Powered Document Generation

```python
# Generate content with LLM
response = llm.generate("Write a summary about...")

# Insert into Google Doc
requests = [{
    'insertText': {
        'location': {'index': 1},
        'text': response.text
    }
}]
service.documents().batchUpdate(documentId=DOC_ID, body={'requests': requests}).execute()
```

### 6. MCP Servers for Google Docs

Several community MCP servers exist for AI assistant integration:

| Server | Features |
|--------|----------|
| [google-docs-mcp](https://github.com/a-bonus/google-docs-mcp) | Full Docs/Sheets/Drive, formatting, comments |
| [google-drive-mcp](https://github.com/piotr-agier/google-drive-mcp) | Drive, Docs, Sheets, Slides |
| [mcp-gdrive](https://github.com/isaacphi/mcp-gdrive) | List, read, search files |

Google has also announced official MCP support for Google services in 2026.

## Proposed Implementation

### A. New Service: `szymon/services/google_docs.py`

```python
"""Google Docs API service."""

from pathlib import Path
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pydantic import BaseModel

SCOPES = ["https://www.googleapis.com/auth/documents"]

class DocumentCreate(BaseModel):
    title: str

class TextInsert(BaseModel):
    index: int
    text: str

class GoogleDocsService:
    """Service for interacting with Google Docs API."""

    def __init__(self, client_id: str, client_secret: str, token_path: Path, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = token_path
        self.redirect_uri = redirect_uri
        self._service = None

    # OAuth methods (same pattern as GoogleTasksService)
    # ...

    def _get_service(self):
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("docs", "v1", credentials=creds)
        return self._service

    # Document Operations

    def create_document(self, title: str) -> dict:
        """Create a new document."""
        service = self._get_service()
        return service.documents().create(body={'title': title}).execute()

    def get_document(self, document_id: str) -> dict:
        """Get document by ID."""
        service = self._get_service()
        return service.documents().get(documentId=document_id).execute()

    def get_document_text(self, document_id: str) -> str:
        """Extract plain text from document."""
        doc = self.get_document(document_id)
        body = doc.get('body', {})
        return self._extract_text(body.get('content', []))

    def _extract_text(self, elements: list) -> str:
        """Recursively extract text from structural elements."""
        text = ''
        for element in elements:
            if 'paragraph' in element:
                for elem in element['paragraph'].get('elements', []):
                    text_run = elem.get('textRun')
                    if text_run:
                        text += text_run.get('content', '')
            elif 'table' in element:
                for row in element['table'].get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        text += self._extract_text(cell.get('content', []))
        return text

    def insert_text(self, document_id: str, index: int, text: str) -> dict:
        """Insert text at specified index."""
        service = self._get_service()
        requests = [{'insertText': {'location': {'index': index}, 'text': text}}]
        return service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()

    def append_text(self, document_id: str, text: str) -> dict:
        """Append text to end of document."""
        doc = self.get_document(document_id)
        end_index = doc['body']['content'][-1]['endIndex'] - 1
        return self.insert_text(document_id, end_index, text)

    def replace_all_text(self, document_id: str, find: str, replace: str) -> dict:
        """Find and replace all occurrences."""
        service = self._get_service()
        requests = [{
            'replaceAllText': {
                'containsText': {'text': find, 'matchCase': True},
                'replaceText': replace
            }
        }]
        return service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()

    def list_recent_documents(self, max_results: int = 10) -> list[dict]:
        """List recent documents (requires Drive API)."""
        # Would need Drive API integration
        raise NotImplementedError("Requires Google Drive service")
```

### B. New Router: `szymon/routers/docs.py`

```python
"""Google Docs API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse

router = APIRouter(prefix="/api/docs", tags=["docs"])

_service: Optional["GoogleDocsService"] = None

def init_service(service: Optional["GoogleDocsService"]):
    global _service
    _service = service

def _require_service():
    if _service is None:
        raise HTTPException(
            status_code=503,
            detail="Google Docs not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )
    return _service

# Auth endpoints
@router.get("/auth/status")
def auth_status():
    service = _require_service()
    return {"authenticated": service.is_authenticated()}

@router.get("/auth/login")
def auth_login():
    service = _require_service()
    url, _ = service.get_auth_url()
    return RedirectResponse(url=url)

@router.get("/auth/callback")
def auth_callback(code: str):
    service = _require_service()
    try:
        service.exchange_code(code)
        return RedirectResponse(url="/")
    except Exception as e:
        return HTMLResponse(f"<h1>Error</h1><p>{e}</p>", status_code=400)

# Document endpoints
@router.post("/documents")
def create_document(title: str):
    service = _require_service()
    return service.create_document(title)

@router.get("/documents/{document_id}")
def get_document(document_id: str):
    service = _require_service()
    return service.get_document(document_id)

@router.get("/documents/{document_id}/text")
def get_document_text(document_id: str):
    service = _require_service()
    return {"text": service.get_document_text(document_id)}

@router.post("/documents/{document_id}/insert")
def insert_text(document_id: str, index: int, text: str):
    service = _require_service()
    return service.insert_text(document_id, index, text)

@router.post("/documents/{document_id}/append")
def append_text(document_id: str, text: str):
    service = _require_service()
    return service.append_text(document_id, text)
```

### C. Configuration Updates

**In `main.py`:**
```python
from szymon.services.google_docs import GoogleDocsService
from szymon.routers import docs as docs_router

def _init_google_docs() -> Optional[GoogleDocsService]:
    if not settings.google_client_id or not settings.google_client_secret:
        return None
    return GoogleDocsService(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_path=settings.google_docs_token_path,  # New setting
        redirect_uri=f"https://{settings.host}:{settings.port}/api/docs/auth/callback",
    )

docs_router.init_service(_init_google_docs())
app.include_router(docs_router.router)
```

### D. Shared OAuth Credentials (Future Enhancement)

Consider a unified Google service that shares credentials across Tasks, Docs, Calendar, Drive:

```python
class GoogleAuthService:
    """Shared OAuth service for all Google APIs."""

    SCOPES = [
        "https://www.googleapis.com/auth/tasks",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def get_credentials(self) -> Credentials:
        # Shared credential management
        pass
```

## Use Cases for Your Personal Assistant

### 1. Document Summarization
- Fetch document text via API
- Send to LLM for summary
- Store/display summary in dashboard

### 2. Meeting Notes Processing
- Extract action items from meeting notes
- Create tasks in Google Tasks
- Update project documents

### 3. Knowledge Base / RAG
- Index your documents for semantic search
- Query documents using natural language
- Get contextual answers with citations

### 4. Document Templates
- LLM generates content from prompts
- Insert into Google Docs templates
- Automated report generation

### 5. Voice-to-Document
- Transcribe audio (Whisper API)
- Format and structure via LLM
- Create Google Doc with result

## Code References

- `szymon/services/google_tasks.py:29-199` - Existing Google service pattern
- `szymon/routers/tasks.py:10-88` - Router pattern with auth flow
- `szymon/main.py:21-44` - Settings configuration
- `szymon/main.py:49-63` - Service initialization pattern

## Architecture Insights

1. **Service Layer Pattern**: Encapsulate all API logic in service classes
2. **Lazy Initialization**: Build API clients on first use, not at startup
3. **Module Singleton**: Inject services at module level for dependency management
4. **Guard Pattern**: `_require_service()` ensures proper 503 responses
5. **Pydantic Models**: Use for request/response validation

## Open Questions

1. **Shared vs Separate Tokens**: Should Docs share OAuth token with Tasks, or use separate?
   - Separate is simpler initially but requires multiple auth flows
   - Shared is better UX but needs scope management

2. **Drive Integration**: Listing documents requires Drive API - add now or later?

3. **MCP Server**: Build custom MCP server for this assistant, or use existing community ones?

4. **RAG Backend**: Which vector database for document embeddings?
   - pgvector (if adding Postgres)
   - ChromaDB (simple, local)
   - Pinecone (managed, scalable)

5. **Real-time Sync**: How to handle document changes for RAG index updates?

## Related Research

- `thoughts/shared/plans/google-tasks-router-refactor.md` - Related refactoring plans
- `thoughts/shared/research/2026-02-01_google-tasks-refactor.md` - Google Tasks research
- `thoughts/shared/plans/minimal-calendar-design-system.md` - Calendar integration plans

## External Resources

- [Google Docs API Overview](https://developers.google.com/workspace/docs/api/how-tos/overview)
- [Python Quickstart](https://developers.google.com/workspace/docs/api/quickstart/python)
- [batchUpdate Reference](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate)
- [LangChain Google Drive Loader](https://python.langchain.com/docs/integrations/document_loaders/google_drive)
- [Gemini File Search](https://ai.google.dev/gemini-api/docs/file-search)
