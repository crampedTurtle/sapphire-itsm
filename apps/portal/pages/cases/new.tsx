import { useState } from 'react'
import { useRouter } from 'next/router'
import axios from 'axios'
import { useAuth } from '../../contexts/AuthContext'
import { AuthGuard } from '../../components/AuthGuard'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function NewCasePageContent() {
  const router = useRouter()
  const { email, tenantId, isAuthenticated } = useAuth()
  const [formData, setFormData] = useState({
    title: '',
    category: 'support',
    priority: 'normal',
    description: ''
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [aiResponse, setAiResponse] = useState<any>(null) // For AI auto-resolution

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!isAuthenticated || !email) {
      setError('You must be authenticated to create a case')
      return
    }
    
    setSubmitting(true)
    setError('')
    setAiResponse(null)

    try {
      // Use new AI-first support intake endpoint
      const response = await axios.post(`${API_URL}/v1/support/intakeRequest`, {
        tenant_id: tenantId || undefined, // Will be resolved from email domain if not provided
        user_id: email,
        subject: formData.title,
        message: formData.description,
        category: formData.category,
        priority_requested: formData.priority,
        attachments: [] // TODO: Add file upload support
      })

      // Handle AI auto-resolution vs case creation
      if (response.data.status === 'ai_response') {
        // AI resolved it - show the answer
        setAiResponse(response.data)
        setSubmitting(false)
      } else if (response.data.status === 'case_created') {
        // Case was created - redirect to case page
        router.push(`/cases/${response.data.case_id}`)
      } else {
        throw new Error('Unexpected response format')
      }
    } catch (err: any) {
      console.error('Error creating case:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create case'
      setError(errorMessage)
      setSubmitting(false)
    }
  }

  return (
    <div className="container">
      <header>
        <h1>Open a Support Case</h1>
      </header>

      <main>
        <form onSubmit={handleSubmit} className="case-form">
          {error && (
            <div className="error">
              {error}
            </div>
          )}

          {aiResponse && (
            <div className="ai-response">
              <h3>AI Response</h3>
              <p>{aiResponse.answer}</p>
              {aiResponse.citations && aiResponse.citations.length > 0 && (
                <div className="citations">
                  <h4>Sources:</h4>
                  <ul>
                    {aiResponse.citations.map((citation: any, idx: number) => (
                      <li key={idx}>
                        <a href={citation.url} target="_blank" rel="noopener noreferrer">
                          {citation.title || citation.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {aiResponse.remediation_steps && aiResponse.remediation_steps.length > 0 && (
                <div className="remediation">
                  <h4>Recommended Steps:</h4>
                  <ol>
                    {aiResponse.remediation_steps.map((step: string, idx: number) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}
              <div className="ai-response-actions">
                <button
                  type="button"
                  onClick={async () => {
                    // User wants to escalate - create case anyway
                    try {
                      const response = await axios.post(`${API_URL}/v1/support/intakeRequest`, {
                        tenant_id: tenantId || undefined,
                        user_id: email,
                        subject: formData.title,
                        message: formData.description + '\n\n[User requested escalation after AI response]',
                        category: formData.category,
                        priority_requested: formData.priority,
                        attachments: []
                      })
                      if (response.data.status === 'case_created') {
                        router.push(`/cases/${response.data.case_id}`)
                      }
                    } catch (err: any) {
                      setError('Failed to create case. Please try again.')
                      setAiResponse(null)
                      setSubmitting(false)
                    }
                  }}
                  className="button secondary"
                >
                  This didn't help - Create Case
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAiResponse(null)
                    setSubmitting(false)
                  }}
                  className="button secondary"
                >
                  Ask Another Question
                </button>
                <button
                  type="button"
                  onClick={() => router.push('/cases')}
                  className="button primary"
                >
                  View My Cases
                </button>
              </div>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="title">Title *</label>
            <input
              type="text"
              id="title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="category">Category *</label>
            <select
              id="category"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              required
            >
              <option value="support">Support</option>
              <option value="onboarding">Onboarding</option>
              <option value="billing">Billing</option>
              <option value="compliance">Compliance</option>
              <option value="outage">Outage</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="priority">Priority</label>
            <select
              id="priority"
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="description">Description *</label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={8}
              required
            />
          </div>

          <div className="form-actions">
            <button type="submit" disabled={submitting} className="button primary">
              {submitting ? 'Creating...' : 'Create Case'}
            </button>
            <button type="button" onClick={() => router.back()} className="button secondary">
              Cancel
            </button>
          </div>
        </form>
      </main>

      <style jsx>{`
        .container {
          max-width: 800px;
          margin: 0 auto;
          padding: 2rem;
        }

        header {
          margin-bottom: 2rem;
        }

        .case-form {
          background: white;
          padding: 2rem;
          border-radius: 8px;
          border: 1px solid #ddd;
        }

        .error {
          background: #fee;
          color: #c33;
          padding: 1rem;
          border-radius: 4px;
          margin-bottom: 1rem;
        }

        .form-group {
          margin-bottom: 1.5rem;
        }

        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
          width: 100%;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 1rem;
        }

        .form-group textarea {
          font-family: inherit;
        }

        .form-actions {
          display: flex;
          gap: 1rem;
          margin-top: 2rem;
        }

        .button {
          padding: 0.75rem 2rem;
          border-radius: 4px;
          font-size: 1rem;
          cursor: pointer;
          border: none;
        }

        .button.primary {
          background: #0070f3;
          color: white;
        }

        .button.secondary {
          background: #f5f5f5;
          color: #333;
        }

        .button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .ai-response {
          background: #e8f5e9;
          border: 1px solid #4caf50;
          padding: 1.5rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
        }

        .ai-response h3 {
          margin-top: 0;
          color: #2e7d32;
        }

        .ai-response h4 {
          margin-top: 1rem;
          margin-bottom: 0.5rem;
          font-size: 0.9rem;
          color: #555;
        }

        .citations ul,
        .remediation ol {
          margin: 0.5rem 0;
          padding-left: 1.5rem;
        }

        .citations li,
        .remediation li {
          margin-bottom: 0.25rem;
        }

        .citations a {
          color: #0070f3;
          text-decoration: none;
        }

        .citations a:hover {
          text-decoration: underline;
        }

        .ai-response-actions {
          display: flex;
          gap: 1rem;
          margin-top: 1.5rem;
        }
      `}</style>
    </div>
  )
}

export default function NewCasePage() {
  return (
    <AuthGuard>
      <NewCasePageContent />
    </AuthGuard>
  )
}

