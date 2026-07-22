import { useState } from 'react'
import SearchView from './SearchView'
import GraphView from './GraphView'
import ChatView from './ChatView'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('search')
  const [selectedCourse, setSelectedCourse] = useState(null)

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>PioneerPlanner</h1>
        <nav>
          <button 
            className={activeTab === 'search' ? 'active' : ''} 
            onClick={() => setActiveTab('search')}
          >
            Search Courses
          </button>
          <button 
            className={activeTab === 'graph' ? 'active' : ''} 
            onClick={() => setActiveTab('graph')}
          >
            Prerequisite Graph
          </button>
          <button 
            className={activeTab === 'chat' ? 'active' : ''} 
            onClick={() => setActiveTab('chat')}
          >
            AI Chat
          </button>
        </nav>
      </header>

      <main className="app-content">
        {activeTab === 'search' && (
          <SearchView 
            onCourseSelect={(courseId) => {
              setSelectedCourse(courseId)
              setActiveTab('graph')
            }} 
          />
        )}
        {activeTab === 'graph' && (
          <GraphView courseId={selectedCourse} />
        )}
        {activeTab === 'chat' && (
          <ChatView />
        )}
      </main>
    </div>
  )
}

export default App
