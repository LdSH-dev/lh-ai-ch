import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { searchDocuments } from '../api'

function SearchBar() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [showResults, setShowResults] = useState(false)
  const [searching, setSearching] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      setShowResults(false)
      return
    }

    const debounceTimer = setTimeout(async () => {
      try {
        setSearching(true)
        const data = await searchDocuments(query)
        setResults(data)
        setShowResults(true)
      } catch (err) {
        console.error('Search failed:', err)
      } finally {
        setSearching(false)
      }
    }, 300)

    return () => clearTimeout(debounceTimer)
  }, [query])

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="search-container" ref={containerRef}>
      <div className="search-bar">
        <div className="search-input-wrapper">
          <input
            type="text"
            placeholder="Search documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => results.length > 0 && setShowResults(true)}
          />
          {searching && <span className="search-spinner"></span>}
        </div>
      </div>
      {showResults && (
        <div className="search-results">
          {results.length === 0 ? (
            <div className="result-item">No results found</div>
          ) : (
            results.map(result => (
              <div key={result.id} className="result-item">
                <Link
                  to={`/documents/${result.id}`}
                  onClick={() => setShowResults(false)}
                >
                  {result.filename}
                </Link>
                <div className="snippet">{result.snippet}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default SearchBar
