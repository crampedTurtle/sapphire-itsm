import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import axios from 'axios'
import { useAuth } from '../../contexts/AuthContext'
import { AuthGuard } from '../../components/AuthGuard'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Message {
  id: string
  sender_type: string
  sender_email: string
  body_text: string
  created_at: string
}

interface Case {
  id: string
  title: string
  status: string
  priority: string
  messages: Message[]
  ai_artifacts: any[]
}

function CaseDetailPageContent() {
  const router = useRouter()
  const { id } = router.query
  const { email, isAuthenticated } = useAuth()
  const [caseData, setCaseData] = useState<Case | null>(null)
  const [loading, setLoading] = useState(true)
  const [replyText, setReplyText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (id) {
      fetchCase()
    }
  }, [id])

  const fetchCase = async () => {
    try {
      const response = await axios.get(`${API_URL}/v1/cases/${id}`)
      setCaseData(response.data)
    } catch (error) {
      console.error('Error fetching case:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleReply = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!replyText.trim() || !id) return

    if (!isAuthenticated || !email) {
      alert('You must be authenticated to send a reply')
      return
    }
    
    setSubmitting(true)
    try {
      await axios.post(`${API_URL}/v1/cases/${id}/messages`, {
        sender_email: email,
        body_text: replyText
      })
      setReplyText('')
      fetchCase() // Refresh
    } catch (error) {
      console.error('Error sending reply:', error)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="container">Loading...</div>
  }

  if (!caseData) {
    return <div className="container">Case not found</div>
  }

  return (
    <div className="container">
      <header>
        <h1>{caseData.title}</h1>
        <div className="case-meta">
          <span className={`status status-${caseData.status}`}>
            {caseData.status}
          </span>
          <span>Priority: {caseData.priority}</span>
        </div>
      </header>

      <main>
        <section className="messages-section">
          <h2>Messages</h2>
          <div className="messages">
            {caseData.messages.map((message) => (
              <div key={message.id} className={`message message-${message.sender_type}`}>
                <div className="message-header">
                  <strong>{message.sender_email}</strong>
                  <span>{new Date(message.created_at).toLocaleString()}</span>
                </div>
                <div className="message-body">
                  {message.body_text}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="reply-section">
          <h2>Add Reply</h2>
          <form onSubmit={handleReply}>
            <textarea
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Type your reply..."
              rows={6}
            />
            <button type="submit" disabled={submitting || !replyText.trim()}>
              {submitting ? 'Sending...' : 'Send Reply'}
            </button>
          </form>
        </section>

        {caseData.ai_artifacts && caseData.ai_artifacts.length > 0 && (
          <section className="ai-section">
            <h2>AI Summary</h2>
            {caseData.ai_artifacts
              .filter(a => a.artifact_type === 'summary')
              .map((artifact) => (
                <div key={artifact.id} className="ai-artifact">
                  <p>{artifact.content}</p>
                </div>
              ))}
          </section>
        )}
      </main>

      <style jsx>{`
        .container {
          max-width: 1000px;
          margin: 0 auto;
          padding: 2rem;
        }

        header {
          margin-bottom: 2rem;
        }

        .case-meta {
          display: flex;
          gap: 1rem;
          margin-top: 0.5rem;
        }

        .status {
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.875rem;
          font-weight: 500;
        }

        .status-new { background: #e3f2fd; color: #1976d2; }
        .status-open { background: #fff3e0; color: #f57c00; }
        .status-resolved { background: #e8f5e9; color: #388e3c; }

        .messages-section {
          margin-bottom: 2rem;
        }

        .messages {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .message {
          padding: 1rem;
          border-radius: 8px;
          border: 1px solid #ddd;
        }

        .message-customer {
          background: #f0f7ff;
        }

        .message-agent {
          background: #fff5e6;
        }

        .message-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 0.5rem;
          font-size: 0.875rem;
          color: #666;
        }

        .message-body {
          white-space: pre-wrap;
        }

        .reply-section {
          margin-bottom: 2rem;
        }

        .reply-section textarea {
          width: 100%;
          padding: 1rem;
          border: 1px solid #ddd;
          border-radius: 4px;
          margin-bottom: 1rem;
          font-family: inherit;
        }

        .reply-section button {
          padding: 0.75rem 2rem;
          background: #0070f3;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        .reply-section button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .ai-section {
          background: #f9f9f9;
          padding: 1.5rem;
          border-radius: 8px;
        }

        .ai-artifact {
          margin-top: 1rem;
        }
      `}</style>
    </div>
  )
}

export default function CaseDetailPage() {
  return (
    <AuthGuard>
      <CaseDetailPageContent />
    </AuthGuard>
  )
}

