# Findings

## PERF-001: N+1 Query Problem in Documents Listing

**Type:** PERFORMANCE

### Summary

The `list_documents` endpoint in `documents.py` suffered from the classic N+1 Query Problem. For each document returned, a separate database query was executed to fetch its `ProcessingStatus`.

**Problematic code:**
```python
@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document))  # 1 query
    documents = result.scalars().all()

    response = []
    for doc in documents:
        # N additional queries - one per document!
        status_result = await db.execute(
            select(ProcessingStatus).where(ProcessingStatus.document_id == doc.id)
        )
        status = status_result.scalar_one_or_none()
        response.append(DocumentResponse(...))

    return response
```

This is a critical performance issue because:

1. **Linear query growth** - If there are 100 documents, 101 queries are executed (1 + 100)
2. **Database connection overhead** - Each query incurs network round-trip latency
3. **Poor scalability** - Response time degrades linearly with dataset size
4. **Resource waste** - Excessive database load and connection pool exhaustion under load

### Solution

Implemented **eager loading** using SQLAlchemy's `selectinload()` strategy. This loads the related `ProcessingStatus` records in a single additional query, reducing total queries from N+1 to just 2 (one for documents, one for all related statuses).

**Fixed code:**
```python
from sqlalchemy.orm import selectinload

@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    # Use selectinload to eager load processing_status in a single query
    # This avoids the N+1 query problem
    result = await db.execute(
        select(Document).options(selectinload(Document.processing_status))
    )
    documents = result.scalars().all()

    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size,
            page_count=doc.page_count,
            status=doc.processing_status.status if doc.processing_status else "unknown",
            created_at=doc.created_at,
        )
        for doc in documents
    ]
```

### Performance Impact

| Scenario | Before (N+1) | After (Eager Load) |
|----------|--------------|-------------------|
| 10 documents | 11 queries | 2 queries |
| 100 documents | 101 queries | 2 queries |
| 1000 documents | 1001 queries | 2 queries |

### Files Changed

- `backend/app/routes/documents.py`

---

## SEC-004: Permissive CORS with Credentials

**Type:** SECURITY

### Summary

The `main.py` file contained an insecure CORS configuration that combined `allow_origins=["*"]` with `allow_credentials=True`.

**Vulnerable code:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This combination is a critical vulnerability because:

1. **Cross-Site Request Forgery (CSRF)** - Any malicious website can make authenticated requests on behalf of the user
2. **Credential theft** - An attacker can create a site that extracts sensitive data from the authenticated user
3. **Same-Origin Policy violation** - The browser's natural protection is completely bypassed
4. **Full API exposure** - All HTTP methods and headers are allowed without restriction

### Solution

Implemented a restrictive CORS configuration following best practices:

1. **Explicit origins** - Allowed origins are defined via the `CORS_ORIGINS` environment variable
2. **Boot-time validation** - The application fails to start if `CORS_ORIGINS` is not defined
3. **Restricted methods** - Only `GET`, `POST`, `PUT`, `DELETE` are allowed (not `["*"]`)
4. **Restricted headers** - Only `Authorization` and `Content-Type` are allowed (not `["*"]`)

**Fixed code in `config.py`:**
```python
class Settings:
    # ...
    CORS_ORIGINS: list[str] = []

    def __init__(self):
        self._parse_cors_origins()
        self._validate_required_vars()

    def _parse_cors_origins(self):
        """Parse CORS_ORIGINS from environment variable."""
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            self.CORS_ORIGINS = [
                origin.strip() 
                for origin in cors_env.split(",") 
                if origin.strip()
            ]
```

**Fixed code in `main.py`:**
```python
from app.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Docker Compose updated:**
```yaml
environment:
  CORS_ORIGINS: ${CORS_ORIGINS:?CORS_ORIGINS is required}
```

### Required Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `CORS_ORIGINS` | Yes | Comma-separated list of allowed origins | `http://localhost:5173,https://app.example.com` |

### Files Changed

- `backend/app/config.py`
- `backend/app/main.py`
- `docker-compose.yml`

---

## SEC-003: Hardcoded Credentials in Configuration

**Type:** SECURITY

### Summary

The `config.py` file contained hardcoded sensitive credentials directly in the source code, including the database password and a secret key.

**Vulnerable code:**
```python
class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:supersecretpassword123@localhost:5432/docproc"
    )
    SECRET_KEY: str = "my-super-secret-key-do-not-share"
```

This is a critical security issue because:
1. **Credentials in version control** - Anyone with access to the repository can see the credentials
2. **No environment separation** - The same credentials would be used in dev, test, and production
3. **Difficult rotation** - Changing credentials requires code changes and redeployment
4. **Audit trail issues** - No way to track who accessed the credentials

### Solution

Implemented a secure configuration approach following best practices:

1. **Environment variables only** - All sensitive values must come from environment variables with no fallback defaults for required security values
2. **Validation at startup** - Added a `_validate_required_vars()` method that checks for required environment variables at application boot time, failing fast with a clear error message if any are missing
3. **Docker Compose integration** - Updated `docker-compose.yml` to use environment variable substitution with the `${VAR:?error}` syntax for required variables
4. **Environment template** - Created `.env.example` documenting all required and optional environment variables

**Fixed code:**
```python
import os


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/tmp/docproc_uploads")

    def __init__(self):
        self._validate_required_vars()

    def _validate_required_vars(self):
        """Valida variáveis obrigatórias no boot da aplicação."""
        missing = []
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        if not self.SECRET_KEY:
            missing.append("SECRET_KEY")
        
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Please set them before starting the application."
            )


settings = Settings()
```

**Docker Compose updated:**
```yaml
environment:
  DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@db:5432/docproc}
  SECRET_KEY: ${SECRET_KEY:?SECRET_KEY is required}
```

### Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | Secret key for signing tokens/sessions |
| `POSTGRES_USER` | No | PostgreSQL username (default: postgres) |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_DB` | No | PostgreSQL database name (default: docproc) |
| `UPLOAD_DIR` | No | File upload directory (default: /tmp/docproc_uploads) |

### Files Changed

- `backend/app/config.py`
- `docker-compose.yml`
- `.env.example` (new file)

---

## SEC-001: SQL Injection in Search Endpoint

**Type:** SECURITY

### Summary

The search endpoint in `search.py` was vulnerable to SQL Injection attacks. The query was constructed using Python f-string interpolation, directly embedding user input into the SQL query without any sanitization or parameterization.

**Vulnerable code:**
```python
query = text(f"SELECT id, filename, content FROM documents WHERE content ILIKE '%{q}%'")
```

An attacker could exploit this by sending malicious input like `'; DROP TABLE documents; --` to manipulate the database.

### Solution

Replaced the f-string interpolation with SQLAlchemy's parameterized queries (bound parameters). This ensures that user input is properly escaped and treated as data, not as executable SQL code.

**Fixed code:**
```python
query = text("SELECT id, filename, content FROM documents WHERE content ILIKE :search_term")
result = await db.execute(query, {"search_term": f"%{q}%"})
```

The `:search_term` placeholder is replaced by SQLAlchemy with the properly escaped value from the parameters dictionary, preventing any SQL injection attempts.

### Files Changed

- `backend/app/routes/search.py`

---

## BUG-001: SearchBar UX Issues

**Type:** BUG

### Summary

The SearchBar component had multiple UX issues:

1. **Search results not closing on outside click** - When clicking outside the search input and results dropdown, the results remained visible instead of closing automatically.

2. **Manual search required** - Users had to click the "Search" button or press Enter to trigger a search, instead of having automatic search-as-you-type functionality.

3. **Layout shift during search** - The search button text changed from "Search" to "..." during loading, causing a visual layout jump due to the different text widths.

### Solution

1. **Click outside detection** - Added a `useRef` on the container element combined with a `useEffect` that listens to `mousedown` events on the document. When a click occurs outside the container, the results are hidden.

2. **Automatic search with debounce** - Replaced the form submission handler with a `useEffect` that watches the query state. Implemented a 300ms debounce timer to avoid excessive API calls while the user is still typing.

3. **Fixed-position spinner** - Replaced the button with a circular spinner positioned absolutely inside the input field (on the right side). This prevents any layout shifts since the spinner doesn't affect the document flow.

### Files Changed

- `frontend/src/components/SearchBar.jsx`
- `frontend/src/App.css`

---

## SEC-002: Path Traversal in File Upload

**Type:** SECURITY

### Summary

The document upload endpoint in `documents.py` was vulnerable to Path Traversal attacks. The filename provided by the user (`file.filename`) was used directly to construct the file path without any sanitization.

**Vulnerable code:**
```python
file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
```

An attacker could exploit this by uploading a file with a malicious name like `../../../etc/cron.d/malicious` or `..\..\..\..\Windows\System32\config` to write files outside the intended upload directory, potentially overwriting critical system files or planting malicious scripts.

### Solution

Implemented a multi-layer defense approach:

1. **`sanitize_filename()` function** - Sanitizes the filename by:
   - Extracting only the base filename using `os.path.basename()` (removes path components like `../`)
   - Removing null bytes (`\x00`) which can be used to bypass checks
   - Replacing potentially dangerous characters with underscores (keeps only `[a-zA-Z0-9._-]`)
   - Rejecting empty filenames or special names like `.` and `..`
   - Adding a UUID prefix to prevent filename collisions

2. **`validate_file_path()` function** - Secondary validation that:
   - Resolves the final path using `os.path.realpath()`
   - Verifies the resolved path starts with the upload directory
   - Prevents any bypasses through symlinks or other path manipulation

**Fixed code:**
```python
def sanitize_filename(filename: str) -> str:
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    safe_name = os.path.basename(filename)
    safe_name = safe_name.replace('\x00', '')
    safe_name = re.sub(r'[^\w.\-]', '_', safe_name)
    
    if not safe_name or safe_name in ('.', '..'):
        raise ValueError("Invalid filename after sanitization")
    
    unique_prefix = uuid.uuid4().hex[:8]
    safe_name = f"{unique_prefix}_{safe_name}"
    
    return safe_name

# In the endpoint:
safe_filename = sanitize_filename(file.filename)
file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

if not validate_file_path(settings.UPLOAD_DIR, file_path):
    raise HTTPException(status_code=400, detail="Invalid file path")
```

### Files Changed

- `backend/app/routes/documents.py`

