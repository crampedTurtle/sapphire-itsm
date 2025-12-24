import { useState } from 'react'
import { useRouter } from 'next/router'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function NewCasePage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    title: '',
    category: 'support',
    priority: 'normal',
    description: ''
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      // In production, tenant_id and email would come from auth context
      // tenant_id is optional - will be resolved from email domain if not provided
      const response = await axios.post(`${API_URL}/v1/intake/portal`, {
        from_email: 'user@example.com', // Placeholder - in production, get from auth
        category: formData.category,
        title: formData.title,
        priority: formData.priority,
        description: formData.description
      })

      router.push(`/cases/${response.data.case_id}`)
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
      `}</style>
    </div>
  )
}

