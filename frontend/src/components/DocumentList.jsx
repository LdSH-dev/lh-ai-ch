import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getDocuments } from '../api'

const PAGE_SIZE = 20

/**
 * DocumentList component displays a paginated list of documents.
 * 
 * @param {Object} props
 * @param {number} props.refreshKey - A key that triggers a data refresh when changed.
 *                                    Used by parent components to signal that the list
 *                                    should be reloaded (e.g., after a new upload).
 */
function DocumentList({ refreshKey }) {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: PAGE_SIZE,
    total: 0,
    totalPages: 1,
  })

  // Reload documents when page changes or when refreshKey changes (e.g., after upload)
  useEffect(() => {
    loadDocuments(pagination.page)
  }, [pagination.page, refreshKey])

  async function loadDocuments(page) {
    try {
      setLoading(true)
      const data = await getDocuments(page, PAGE_SIZE)
      setDocuments(data.items)
      setPagination(prev => ({
        ...prev,
        total: data.total,
        totalPages: data.total_pages,
      }))
    } catch (err) {
      setError('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  function goToPage(page) {
    if (page >= 1 && page <= pagination.totalPages) {
      setPagination(prev => ({ ...prev, page }))
    }
  }

  if (loading && documents.length === 0) {
    return <div className="loading">Loading documents...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  return (
    <div className="document-list">
      <div className="document-list-header">
        <h2>Documents</h2>
        {pagination.total > 0 && (
          <span className="document-count">{pagination.total} document{pagination.total !== 1 ? 's' : ''}</span>
        )}
      </div>
      {documents.length === 0 ? (
        <div className="empty-state">
          No documents uploaded yet. Upload a PDF to get started.
        </div>
      ) : (
        <>
          {documents.map(doc => (
            <div key={doc.id} className="document-item">
              <div>
                <Link to={`/documents/${doc.id}`}>{doc.filename}</Link>
                <div className="document-meta">
                  {doc.page_count} pages | {formatFileSize(doc.file_size)} | {doc.status}
                </div>
              </div>
              <div className="document-meta">
                {new Date(doc.created_at).toLocaleDateString()}
              </div>
            </div>
          ))}
          
          {pagination.totalPages > 1 && (
            <div className="pagination">
              <button 
                className="pagination-btn"
                onClick={() => goToPage(1)}
                disabled={pagination.page === 1 || loading}
                title="First page"
              >
                ««
              </button>
              <button 
                className="pagination-btn"
                onClick={() => goToPage(pagination.page - 1)}
                disabled={pagination.page === 1 || loading}
                title="Previous page"
              >
                «
              </button>
              
              <span className="pagination-info">
                Page {pagination.page} of {pagination.totalPages}
              </span>
              
              <button 
                className="pagination-btn"
                onClick={() => goToPage(pagination.page + 1)}
                disabled={pagination.page === pagination.totalPages || loading}
                title="Next page"
              >
                »
              </button>
              <button 
                className="pagination-btn"
                onClick={() => goToPage(pagination.totalPages)}
                disabled={pagination.page === pagination.totalPages || loading}
                title="Last page"
              >
                »»
              </button>
            </div>
          )}
        </>
      )}
      {loading && documents.length > 0 && (
        <div className="loading-overlay">Loading...</div>
      )}
    </div>
  )
}

function formatFileSize(bytes) {
  if (!bytes) return 'Unknown size'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

export default DocumentList
