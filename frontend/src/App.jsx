import { useState, useCallback } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import DocumentList from './components/DocumentList'
import DocumentDetail from './components/DocumentDetail'
import UploadForm from './components/UploadForm'
import SearchBar from './components/SearchBar'

function App() {
  // Key used to trigger a refresh of the DocumentList when a new document is uploaded
  const [refreshKey, setRefreshKey] = useState(0)

  // Callback passed to UploadForm to trigger a refresh after successful upload
  const handleUploadSuccess = useCallback(() => {
    setRefreshKey(prev => prev + 1)
  }, [])

  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="logo">
          <h1>DocProc</h1>
        </Link>
        <nav>
          <SearchBar />
        </nav>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={
            <>
              <UploadForm onUploadSuccess={handleUploadSuccess} />
              <DocumentList refreshKey={refreshKey} />
            </>
          } />
          <Route path="/documents/:id" element={<DocumentDetail />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
