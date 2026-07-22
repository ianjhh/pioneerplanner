"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { ChatMessage } from "@/types/api";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'ai', text: 'Hello! I am PioneerPlanner AI. How can I help you with your academic path today?' }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const wsRef = useRef<WebSocket | null>(null);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  useEffect(() => {
    // Initialize WebSocket connection
    wsRef.current = new WebSocket("ws://localhost:8000/api/v1/chat/ws");
    
    wsRef.current.onmessage = (event) => {
      const data = event.data;
      if (data === "[DONE]") {
        setIsTyping(false);
      } else {
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMsg = newMessages[newMessages.length - 1];
          if (lastMsg.sender === 'ai' && isTyping) {
            lastMsg.text += data;
          } else {
            newMessages.push({ sender: 'ai', text: data });
          }
          return newMessages;
        });
      }
    };
    
    wsRef.current.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsTyping(false);
    };
    
    return () => {
      wsRef.current?.close();
    };
  }, [isTyping]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;
    
    setMessages((prev) => [...prev, { sender: 'user', text: input }]);
    setInput("");
    setIsTyping(true);
    
    // Add empty AI message to be appended to
    setMessages((prev) => [...prev, { sender: 'ai', text: '' }]);
    
    // Send to WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(input);
    } else {
      setMessages((prev) => [...prev, { sender: 'ai', text: '⚠️ Connection lost. Please refresh the page.' }]);
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-4xl mx-auto bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-100 bg-indigo-50/50 flex items-center gap-3">
        <div className="bg-indigo-600 p-2 rounded-lg text-white">
          <Bot className="w-5 h-5" />
        </div>
        <div>
          <h2 className="font-bold text-gray-800">Academic AI Advisor</h2>
          <p className="text-xs text-gray-500">Powered by Local RAG</p>
        </div>
      </div>
      
      {/* Messages Area */}
      <div className="flex-grow overflow-y-auto p-6 space-y-6 bg-gray-50/30">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[80%] gap-3 ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-1 ${
                msg.sender === 'user' ? 'bg-gray-200 text-gray-600' : 'bg-indigo-100 text-indigo-600'
              }`}>
                {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              
              <div className={`p-4 rounded-2xl shadow-sm ${
                msg.sender === 'user' 
                  ? 'bg-indigo-600 text-white rounded-tr-none' 
                  : 'bg-white border border-gray-100 text-gray-800 rounded-tl-none'
              }`}>
                <p className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.text}</p>
                {msg.sender === 'ai' && msg.text === '' && isTyping && (
                  <div className="flex space-x-1 mt-2 h-4 items-center">
                    <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input Area */}
      <div className="p-4 border-t border-gray-100 bg-white">
        <form onSubmit={handleSend} className="relative flex items-center">
          <input
            type="text"
            className="w-full pl-4 pr-14 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
            placeholder="Ask about courses, prerequisites, or degree plans..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isTyping}
          />
          <button
            type="submit"
            disabled={!input.trim() || isTyping}
            className="absolute right-2 p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:bg-gray-400 transition-colors flex items-center justify-center"
          >
            {isTyping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </form>
        <p className="text-center text-xs text-gray-400 mt-2">
          AI can make mistakes. Verify critical prerequisites with official catalog data.
        </p>
      </div>
    </div>
  );
}
