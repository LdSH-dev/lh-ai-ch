import { useState, useEffect } from 'react'
import { getTags, createTag, deleteTag, addTagToDocument, removeTagFromDocument } from '../api'

/**
 * TagManager component for managing tags on a document.
 * 
 * @param {Object} props
 * @param {number} props.documentId - The document ID to manage tags for
 * @param {Array} props.currentTags - Array of tags currently on the document
 * @param {Function} props.onTagsChange - Callback when tags are modified
 */
function TagManager({ documentId, currentTags = [], onTagsChange }) {
  const [allTags, setAllTags] = useState([])
  const [newTagName, setNewTagName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showDropdown, setShowDropdown] = useState(false)

  useEffect(() => {
    loadTags()
  }, [])

  async function loadTags() {
    try {
      const data = await getTags()
      setAllTags(data.items)
    } catch (err) {
      console.error('Failed to load tags:', err)
    }
  }

  async function handleCreateTag(e) {
    e.preventDefault()
    if (!newTagName.trim()) return

    setLoading(true)
    setError(null)

    try {
      const newTag = await createTag(newTagName.trim())
      setAllTags(prev => [...prev, newTag].sort((a, b) => a.name.localeCompare(b.name)))
      setNewTagName('')
      // Automatically add the new tag to the document (pass the tag object directly)
      await handleAddTag(newTag.id, newTag)
    } catch (err) {
      setError(err.detail || 'Failed to create tag')
    } finally {
      setLoading(false)
    }
  }

  async function handleAddTag(tagId, tagObject = null) {
    setLoading(true)
    setError(null)

    try {
      await addTagToDocument(documentId, tagId)
      // Use the passed tag object if available, otherwise find in allTags
      const addedTag = tagObject || allTags.find(t => t.id === tagId)
      if (addedTag && onTagsChange) {
        onTagsChange([...currentTags, addedTag])
      }
    } catch (err) {
      setError(err.detail || 'Failed to add tag')
    } finally {
      setLoading(false)
      setShowDropdown(false)
    }
  }

  async function handleRemoveTag(tagId) {
    setLoading(true)
    setError(null)

    try {
      await removeTagFromDocument(documentId, tagId)
      if (onTagsChange) {
        onTagsChange(currentTags.filter(t => t.id !== tagId))
      }
    } catch (err) {
      setError(err.detail || 'Failed to remove tag')
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteTag(tagId, tagName) {
    if (!confirm(`Delete tag "${tagName}" permanently? It will be removed from all documents.`)) {
      return
    }

    setLoading(true)
    setError(null)

    try {
      await deleteTag(tagId)
      // Remove from local state
      setAllTags(prev => prev.filter(t => t.id !== tagId))
      // Also remove from current document tags if present
      if (onTagsChange && currentTags.some(t => t.id === tagId)) {
        onTagsChange(currentTags.filter(t => t.id !== tagId))
      }
    } catch (err) {
      setError(err.detail || 'Failed to delete tag')
    } finally {
      setLoading(false)
    }
  }

  // Filter out tags that are already on the document
  const availableTags = allTags.filter(
    tag => !currentTags.some(ct => ct.id === tag.id)
  )

  return (
    <div className="tag-manager">
      <div className="tag-manager-header">
        <h4>Tags</h4>
      </div>

      {/* Current tags */}
      <div className="current-tags">
        {currentTags.length === 0 ? (
          <span className="no-tags">No tags</span>
        ) : (
          currentTags.map(tag => (
            <span key={tag.id} className="tag">
              {tag.name}
              <button
                className="tag-remove"
                onClick={() => handleRemoveTag(tag.id)}
                disabled={loading}
                title="Remove tag"
              >
                ×
              </button>
            </span>
          ))
        )}
      </div>

      {/* Add tag dropdown */}
      <div className="tag-add-container">
        <button
          className="tag-add-btn"
          onClick={() => setShowDropdown(!showDropdown)}
          disabled={loading}
        >
          + Add Tag
        </button>

        {showDropdown && (
          <div className="tag-dropdown">
            {/* Create new tag */}
            <form onSubmit={handleCreateTag} className="tag-create-form">
              <input
                type="text"
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                placeholder="New tag name..."
                maxLength={100}
                disabled={loading}
              />
              <button type="submit" disabled={loading || !newTagName.trim()}>
                Create
              </button>
            </form>

            {/* Available tags */}
            {availableTags.length > 0 && (
              <div className="tag-list">
                <div className="tag-list-label">Available tags:</div>
                {availableTags.map(tag => (
                  <div key={tag.id} className="tag-option-row">
                    <button
                      className="tag-option"
                      onClick={() => handleAddTag(tag.id)}
                      disabled={loading}
                    >
                      {tag.name}
                    </button>
                    <button
                      className="tag-delete-btn"
                      onClick={() => handleDeleteTag(tag.id, tag.name)}
                      disabled={loading}
                      title="Delete tag permanently"
                    >
                      🗑
                    </button>
                  </div>
                ))}
              </div>
            )}

            {availableTags.length === 0 && allTags.length > 0 && (
              <div className="tag-list-empty">All tags are already added</div>
            )}
          </div>
        )}
      </div>

      {error && <div className="tag-error">{error}</div>}
    </div>
  )
}

export default TagManager

