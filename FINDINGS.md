# Findings

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

