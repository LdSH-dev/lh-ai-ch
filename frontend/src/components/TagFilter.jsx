import { useState, useEffect } from 'react'
import { getTags } from '../api'

/**
 * TagFilter component for filtering documents by tag.
 * 
 * @param {Object} props
 * @param {number|null} props.selectedTagId - Currently selected tag ID (null for all)
 * @param {Function} props.onTagSelect - Callback when a tag is selected
 */
function TagFilter({ selectedTagId, onTagSelect }) {
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadTags()
  }, [])

  async function loadTags() {
    try {
      setLoading(true)
      const data = await getTags()
      setTags(data.items)
    } catch (err) {
      console.error('Failed to load tags:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return null
  }

  if (tags.length === 0) {
    return null
  }

  return (
    <div className="tag-filter">
      <span className="tag-filter-label">Filter by tag:</span>
      <div className="tag-filter-options">
        <button
          className={`tag-filter-btn ${selectedTagId === null ? 'active' : ''}`}
          onClick={() => onTagSelect(null)}
        >
          All
        </button>
        {tags.map(tag => (
          <button
            key={tag.id}
            className={`tag-filter-btn ${selectedTagId === tag.id ? 'active' : ''}`}
            onClick={() => onTagSelect(tag.id)}
          >
            {tag.name}
          </button>
        ))}
      </div>
    </div>
  )
}

export default TagFilter

