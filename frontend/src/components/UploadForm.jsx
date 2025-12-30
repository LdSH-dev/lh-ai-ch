import { useState } from 'react'
import { uploadDocument, ApiError } from '../api'

/**
 * UploadForm component for uploading PDF documents.
 * 
 * @param {Object} props
 * @param {Function} props.onUploadSuccess - Callback called after a successful upload.
 *                                           Used to notify parent components to refresh data.
 */
function UploadForm({ onUploadSuccess }) {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file) return

    try {
      setUploading(true)
      setError(null)
      await uploadDocument(file)
      setFile(null)
      e.target.reset()
      // Notify parent component of successful upload instead of full page reload
      if (onUploadSuccess) {
        onUploadSuccess()
      }
    } catch (err) {
      // Extract error message from ApiError or fallback to generic message
      const errorMessage = err instanceof ApiError 
        ? err.detail || err.message 
        : 'Failed to upload document'
      setError(errorMessage)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="upload-form">
      <h2>Upload Document</h2>
      {error && <div className="error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={(e) => setFile(e.target.files[0])}
          disabled={uploading}
        />
        <button type="submit" disabled={!file || uploading}>
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>
    </div>
  )
}

export default UploadForm
