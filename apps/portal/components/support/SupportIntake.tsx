import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/router'
import axios from 'axios'
import { useAuth } from '../../contexts/AuthContext'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
  confidence?: number
  citations?: Array<{ title: string; url: string }>
  steps?: string[]
  clarifying_question?: string
  case_id?: string
}

interface KBSuggestion {
  id: string
  title: string
  url: string
  snippet: string
}

export function SupportIntake() {
  const router = useRouter()
  const { email, tenantId, isAuthenticated } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [kbSearchQuery, setKbSearchQuery] = useState('')
  const [kbSuggestions, setKbSuggestions] = useState<KBSuggestion[]>([])
  const [showKbSuggestions, setShowKbSuggestions] = useState(false)
  const [selectedKbArticle, setSelectedKbArticle] = useState<KBSuggestion | null>(null)
  const [helpfulFeedback, setHelpfulFeedback] = useState<{ [key: string]: boolean | null }>({})
  const [escalating, setEscalating] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const kbSearchTimeoutRef = useRef<NodeJS.Timeout>()

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // KB search with debounce
  useEffect(() => {
    if (kbSearchTimeoutRef.current) {
      clearTimeout(kbSearchTimeoutRef.current)
    }

    if (kbSearchQuery.trim().length > 2) {
      kbSearchTimeoutRef.current = setTimeout(async () => {
        try {
          // Note: This endpoint needs to be created in the backend
          // For now, using a placeholder - you'll need to implement GET /v1/kb/search
          const response = await axios.get(`${API_URL}/v1/portal/ask`, {
            params: { question: kbSearchQuery }
          })
          // Transform response to suggestions format
          // This is a placeholder - adjust based on actual API response
          setKbSuggestions([])
        } catch (error) {
          console.error('KB search error:', error)
        }
      }, 300)
    } else {
      setKbSuggestions([])
    }

    return () => {
      if (kbSearchTimeoutRef.current) {
        clearTimeout(kbSearchTimeoutRef.current)
      }
    }
  }, [kbSearchQuery])

  const handleSendMessage = async () => {
    if (!inputText.trim() || !isAuthenticated || !email) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputText,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsTyping(true)

    try {
      const response = await axios.post(`${API_URL}/v1/support/intakeRequest`, {
        tenant_id: tenantId || undefined,
        user_id: email,
        subject: inputText.substring(0, 100), // Use first 100 chars as subject
        message: inputText,
        category: 'support',
        priority_requested: 'normal',
        attachments: []
      })

      setIsTyping(false)

      if (response.data.status === 'ai_response') {
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'ai',
          content: response.data.answer || response.data.message || 'I received your message.',
          timestamp: new Date(),
          confidence: response.data.confidence,
          citations: response.data.citations,
          steps: response.data.steps,
          clarifying_question: response.data.clarifying_question
        }
        setMessages(prev => [...prev, aiMessage])
      } else if (response.data.status === 'case_created') {
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'ai',
          content: `I've created a support case for you. Case ID: ${response.data.case_id}`,
          timestamp: new Date(),
          confidence: response.data.ai_confidence,
          case_id: response.data.case_id
        }
        setMessages(prev => [...prev, aiMessage])
      }
    } catch (error: any) {
      setIsTyping(false)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: `Sorry, I encountered an error: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleHelpfulFeedback = (messageId: string, helpful: boolean) => {
    setHelpfulFeedback(prev => ({ ...prev, [messageId]: helpful }))
    // TODO: Send feedback to backend
  }

  const handleEscalate = async (caseId: string) => {
    if (!caseId) return

    setEscalating(true)
    try {
      await axios.post(`${API_URL}/v1/support/escalate`, {
        case_id: caseId,
        reason: 'User requested escalation from chat'
      })
      
      // Update message to show escalation status
      setMessages(prev => prev.map(msg => 
        msg.case_id === caseId 
          ? { ...msg, content: `${msg.content}\n\n✓ Case has been escalated to support team.` }
          : msg
      ))
    } catch (error: any) {
      console.error('Escalation error:', error)
      alert('Failed to escalate case. Please try again.')
    } finally {
      setEscalating(false)
    }
  }

  const handleKBSuggestionClick = (suggestion: KBSuggestion) => {
    setSelectedKbArticle(suggestion)
    setShowKbSuggestions(false)
    setKbSearchQuery('')
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* KB Search Bar */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="relative max-w-4xl mx-auto">
          <input
            type="text"
            value={kbSearchQuery}
            onChange={(e) => {
              setKbSearchQuery(e.target.value)
              setShowKbSuggestions(true)
            }}
            onFocus={() => setShowKbSuggestions(kbSuggestions.length > 0)}
            placeholder="Search knowledge base..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0A2540] focus:border-transparent"
          />
          {showKbSuggestions && kbSuggestions.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {kbSuggestions.map((suggestion) => (
                <button
                  key={suggestion.id}
                  onClick={() => handleKBSuggestionClick(suggestion)}
                  className="w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                >
                  <div className="font-medium text-[#0A2540]">{suggestion.title}</div>
                  <div className="text-sm text-gray-600 mt-1">{suggestion.snippet}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-12">
              <h2 className="text-2xl font-semibold text-[#0A2540] mb-2">How can we help you?</h2>
              <p>Ask a question or describe your issue, and we'll help you right away.</p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
            >
              <div
                className={`max-w-3xl rounded-2xl px-4 py-3 shadow-sm ${
                  message.type === 'user'
                    ? 'bg-[#0A2540] text-white'
                    : 'bg-white border border-gray-200 text-gray-900'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>

                {/* Steps */}
                {message.steps && message.steps.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="font-semibold mb-2">Steps to resolve:</div>
                    <ol className="list-decimal list-inside space-y-1">
                      {message.steps.map((step, idx) => (
                        <li key={idx} className="text-sm">{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Citations */}
                {message.citations && message.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="font-semibold mb-2">Sources:</div>
                    <ul className="space-y-1">
                      {message.citations.map((citation, idx) => (
                        <li key={idx}>
                          <a
                            href={citation.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-blue-600 hover:underline"
                          >
                            {citation.title}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Clarifying Question */}
                {message.clarifying_question && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="font-semibold mb-2">To help me better assist you:</div>
                    <div className="text-sm italic">{message.clarifying_question}</div>
                  </div>
                )}

                {/* Helpful Feedback */}
                {message.type === 'ai' && message.confidence !== undefined && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    {message.confidence >= 0.78 ? (
                      <div>
                        <div className="text-sm mb-2">Was this helpful?</div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleHelpfulFeedback(message.id, true)}
                            className={`px-3 py-1 text-sm rounded ${
                              helpfulFeedback[message.id] === true
                                ? 'bg-green-100 text-green-700'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                          >
                            ✓ Yes
                          </button>
                          <button
                            onClick={() => handleHelpfulFeedback(message.id, false)}
                            className={`px-3 py-1 text-sm rounded ${
                              helpfulFeedback[message.id] === false
                                ? 'bg-red-100 text-red-700'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                          >
                            ✗ No
                          </button>
                        </div>
                      </div>
                    ) : message.confidence >= 0.45 ? (
                      <div className="text-sm text-gray-600">
                        I need a bit more information to help you better.
                      </div>
                    ) : (
                      <div className="mt-2">
                        <button
                          onClick={() => message.case_id && handleEscalate(message.case_id)}
                          disabled={escalating || !message.case_id}
                          className="px-4 py-2 bg-[#0A2540] text-white rounded-lg hover:bg-[#0d3252] disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                        >
                          {escalating ? 'Escalating...' : 'Escalate to Agent'}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* Case Created */}
                {message.case_id && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="text-sm">
                      <div className="font-semibold mb-1">Support Case Created</div>
                      <div className="text-gray-600 mb-2">Case ID: {message.case_id}</div>
                      <button
                        onClick={() => router.push(`/cases/${message.case_id}`)}
                        className="text-blue-600 hover:underline text-sm"
                      >
                        View Ticket →
                      </button>
                    </div>
                  </div>
                )}

                <div className="text-xs text-gray-400 mt-2">
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex justify-start animate-fade-in">
              <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Message Input */}
      <div className="bg-white border-t border-gray-200 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-2">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
              rows={3}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0A2540] focus:border-transparent resize-none"
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputText.trim() || isTyping}
              className="px-6 py-2 bg-[#0A2540] text-white rounded-lg hover:bg-[#0d3252] disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* KB Article Modal */}
      {selectedKbArticle && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedKbArticle(null)}
        >
          <div
            className="bg-white rounded-lg max-w-3xl w-full max-h-[80vh] overflow-y-auto p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-2xl font-semibold text-[#0A2540]">{selectedKbArticle.title}</h2>
              <button
                onClick={() => setSelectedKbArticle(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            <div className="text-gray-700 mb-4">{selectedKbArticle.snippet}</div>
            <a
              href={selectedKbArticle.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              Read full article →
            </a>
          </div>
        </div>
      )}
    </div>
  )
}

