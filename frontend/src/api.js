const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE}/documents`, {
    method: 'POST',
    body: formData,
  });
  return response.json();
}

export async function getDocuments(page = 1, pageSize = 20) {
  const response = await fetch(`${API_BASE}/documents?page=${page}&page_size=${pageSize}`);
  return response.json();
}

export async function getDocument(id) {
  const response = await fetch(`${API_BASE}/documents/${id}`);
  return response.json();
}

export async function deleteDocument(id) {
  const response = await fetch(`${API_BASE}/documents/${id}`, {
    method: 'DELETE',
  });
  return response.json();
}

export async function searchDocuments(query) {
  const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
  return response.json();
}
