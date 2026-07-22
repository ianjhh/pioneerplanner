import { useState } from 'react'

export default function SearchView({ onCourseSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/v1/search?q=${encodeURIComponent(query)}`)
      const data = await response.json()
      setResults(data.results || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="search-view">
      <h2>Semantic Course Search</h2>
      <form onSubmit={handleSearch} className="search-form">
        <input 
          type="text" 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for courses (e.g. 'Software Engineering' or 'CS 321')" 
        />
        <button type="submit" disabled={loading}>Search</button>
      </form>

      <div className="results-container">
        {loading ? (
          <p>Searching...</p>
        ) : (
          results.map(course => (
            <div key={course.course_id} className="course-card">
              <h3>{course.course_id}: {course.title}</h3>
              <p className="units">{course.units} units | {course.department}</p>
              <p className="desc">{course.description}</p>
              <button onClick={() => onCourseSelect(course.course_id)}>
                View Prerequisites
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
