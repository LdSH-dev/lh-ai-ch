const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Custom error class for API errors.
 * Contains HTTP status code, status text, and parsed error detail from the server.
 */
export class ApiError extends Error {
  constructor(status, statusText, detail) {
    const message = detail || statusText || `HTTP Error ${status}`;
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.detail = detail;
  }
}

/**
 * Handles the fetch response, checking for HTTP errors.
 * 
 * If the response is not ok (status outside 200-299):
 * - Attempts to parse the error detail from the response body
 * - Throws an ApiError with status, statusText, and detail
 * 
 * If the response is ok:
 * - Returns the parsed JSON body
 * 
 * @param {Response} response - The fetch Response object
 * @returns {Promise<any>} The parsed JSON response
 * @throws {ApiError} If the response status is not ok
 */
async function handleResponse(response) {
  if (!response.ok) {
    let detail = null;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || errorBody.message || JSON.stringify(errorBody);
    } catch {
      // Response body is not JSON or empty
    }
    throw new ApiError(response.status, response.statusText, detail);
  }
  return response.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE}/documents`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse(response);
}

export async function getDocuments(page = 1, pageSize = 20, tagId = null) {
  let url = `${API_BASE}/documents?page=${page}&page_size=${pageSize}`;
  if (tagId !== null) {
    url += `&tag_id=${tagId}`;
  }
  const response = await fetch(url);
  return handleResponse(response);
}

export async function getDocument(id) {
  const response = await fetch(`${API_BASE}/documents/${id}`);
  return handleResponse(response);
}

export async function deleteDocument(id) {
  const response = await fetch(`${API_BASE}/documents/${id}`, {
    method: 'DELETE',
  });
  return handleResponse(response);
}

export async function searchDocuments(query) {
  const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
  return handleResponse(response);
}

// ========== Tag API Functions ==========

export async function getTags() {
  const response = await fetch(`${API_BASE}/tags`);
  return handleResponse(response);
}

export async function createTag(name) {
  const response = await fetch(`${API_BASE}/tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  return handleResponse(response);
}

export async function deleteTag(tagId) {
  const response = await fetch(`${API_BASE}/tags/${tagId}`, {
    method: 'DELETE',
  });
  return handleResponse(response);
}

export async function addTagToDocument(documentId, tagId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/tags/${tagId}`, {
    method: 'POST',
  });
  return handleResponse(response);
}

export async function removeTagFromDocument(documentId, tagId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/tags/${tagId}`, {
    method: 'DELETE',
  });
  return handleResponse(response);
}

export async function getDocumentTags(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/tags`);
  return handleResponse(response);
}
