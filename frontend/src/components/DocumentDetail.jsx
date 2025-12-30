import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getDocument, deleteDocument } from '../api'
import { formatFileSize } from '../utils/formatters'

function DocumentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [document, setDocument] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadDocument()
  }, [id])

  async function loadDocument() {
    try {
      setLoading(true)
      const data = await getDocument(id)
      setDocument(data)
    } catch (err) {
      setError('Failed to load document')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete() {
    if (!confirm('Are you sure you want to delete this document?')) {
      return
    }
    try {
      await deleteDocument(id)
      navigate('/')
    } catch (err) {
      setError('Failed to delete document')
    }
  }

  if (loading) {
    return <div className="loading">Loading document...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  if (!document) {
    return <div className="error">Document not found</div>
  }

  return (
    <div className="document-detail">
      <h2>{document.filename}</h2>
      <div className="meta">
        <p>Status: {document.status}</p>
        <p>Pages: {document.page_count || 'Unknown'}</p>
        <p>Size: {formatFileSize(document.file_size)}</p>
        <p>Uploaded: {new Date(document.created_at).toLocaleString()}</p>
      </div>
      <h3>Extracted Content</h3>
      <div className="content">
        {document.content || 'No content extracted'}
      </div>
      <div className="actions">
        <button className="back-btn" onClick={() => navigate('/')}>
          Back to List
        </button>
        <button className="delete-btn" onClick={handleDelete}>
          Delete Document
        </button>
      </div>
    </div>
  )
}

export default DocumentDetail
