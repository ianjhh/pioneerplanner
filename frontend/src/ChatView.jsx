import { useState, useRef, useEffect } from 'react'

export default function ChatView() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am the PioneerPlanner AI. Ask me about courses or degree planning!' }
  ])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const wsRef = useRef(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    // Scroll to bottom on new message
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const connectWebSocket = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return
    
    wsRef.current = new WebSocket('ws://localhost:8000/api/v1/chat/ws')
    
    wsRef.current.onmessage = (event) => {
      const data = event.data
      if (data === '[DONE]') {
        setIsStreaming(false)
        return
      }
      
      setMessages(prev => {
        const lastMsg = prev[prev.length - 1]
        if (lastMsg.role === 'assistant') {
          return [
            ...prev.slice(0, -1),
            { ...lastMsg, content: lastMsg.content + data }
          ]
        } else {
          return [...prev, { role: 'assistant', content: data }]
        }
      })
    }
    
    wsRef.current.onclose = () => {
      console.log('WebSocket closed')
      setIsStreaming(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket()
    }

    setMessages(prev => [...prev, { role: 'user', content: input }, { role: 'assistant', content: '' }])
    setIsStreaming(true)
    
    // Slight delay to ensure WS is open if just connected
    setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(input)
      }
    }, 100)
    
    setInput('')
  }

  return (
    <div className="chat-view">
      <div className="chat-history">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <strong>{msg.role === 'user' ? 'You' : 'PioneerPlanner'}</strong>
            <p>{msg.content}</p>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="chat-input-form">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..." 
          disabled={isStreaming}
        />
        <button type="submit" disabled={isStreaming || !input.trim()}>
          {isStreaming ? 'Thinking...' : 'Send'}
        </button>
      </form>
    </div>
  )
}
