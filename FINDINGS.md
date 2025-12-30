# Findings

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

