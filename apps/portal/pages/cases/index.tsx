import { useState, useEffect } from 'react'
import Link from 'next/link'
import axios from 'axios'
import { useAuth } from '../../contexts/AuthContext'
import { AuthGuard } from '../../components/AuthGuard'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Case {
  id: string
  title: string
  status: string
  priority: string
  created_at: string
  updated_at: string
}

function CasesPageContent() {
  const { email, tenantId } = useAuth()
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // In production, this would fetch cases for the authenticated user's tenant
    // For now, we'll show a message
    setLoading(false)
  }, [])

  return (
    <div className="container">
      <header>
        <h1>My Cases</h1>
        <Link href="/cases/new" className="button primary">
          Open New Case
        </Link>
      </header>

      <main>
        {loading ? (
          <p>Loading...</p>
        ) : cases.length === 0 ? (
          <div className="empty-state">
            <p>You don't have any open cases.</p>
            <Link href="/cases/new" className="button primary">
              Open Your First Case
            </Link>
          </div>
        ) : (
          <div className="cases-list">
            {cases.map((caseItem) => (
              <Link key={caseItem.id} href={`/cases/${caseItem.id}`} className="case-card">
                <div className="case-header">
                  <h3>{caseItem.title}</h3>
                  <span className={`status status-${caseItem.status}`}>
                    {caseItem.status}
                  </span>
                </div>
                <div className="case-meta">
                  <span>Priority: {caseItem.priority}</span>
                  <span>Updated: {new Date(caseItem.updated_at).toLocaleDateString()}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      <style jsx>{`
        .container {
          max-width: 1000px;
          margin: 0 auto;
          padding: 2rem;
        }

        header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .button {
          padding: 0.75rem 2rem;
          border-radius: 4px;
          text-decoration: none;
          font-weight: 500;
        }

        .button.primary {
          background: #0070f3;
          color: white;
        }

        .empty-state {
          text-align: center;
          padding: 4rem 2rem;
        }

        .cases-list {
          display: grid;
          gap: 1rem;
        }

        .case-card {
          background: white;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 1.5rem;
          text-decoration: none;
          color: inherit;
          display: block;
        }

        .case-card:hover {
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .case-header {
          display: flex;
          justify-content: space-between;
          align-items: start;
          margin-bottom: 1rem;
        }

        .case-header h3 {
          margin: 0;
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
        .status-closed { background: #f5f5f5; color: #666; }

        .case-meta {
          display: flex;
          gap: 1rem;
          color: #666;
          font-size: 0.875rem;
        }
      `}</style>
    </div>
  )
}

export default function CasesPage() {
  return (
    <AuthGuard>
      <CasesPageContent />
    </AuthGuard>
  )
}

