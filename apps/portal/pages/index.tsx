import { useState } from 'react'
import Link from 'next/link'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const handleAsk = async () => {
    if (!question.trim()) return
    
    setLoading(true)
    try {
      const response = await axios.post(`${API_URL}/v1/portal/ask`, {
        question: question
      })
      setAnswer(response.data)
    } catch (error) {
      console.error('Error asking question:', error)
      setAnswer({ answer: 'Sorry, I encountered an error. Please try again.', citations: [] })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <header>
        <h1>Sapphire Legal AI</h1>
        <p>Customer Support Portal</p>
      </header>

      <main>
        <section className="ask-section">
          <h2>Ask Sapphire</h2>
          <p>Get instant answers from our knowledge base</p>
          
          <div className="ask-form">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question..."
              rows={4}
            />
            <button onClick={handleAsk} disabled={loading}>
              {loading ? 'Searching...' : 'Ask'}
            </button>
          </div>

          {answer && (
            <div className="answer-section">
              <div className="answer">
                <h3>Answer:</h3>
                <p>{answer.answer}</p>
              </div>
              
              {answer.citations && answer.citations.length > 0 && (
                <div className="citations">
                  <h4>Sources:</h4>
                  <ul>
                    {answer.citations.map((citation: any, idx: number) => (
                      <li key={idx}>
                        <a href={citation.url} target="_blank" rel="noopener noreferrer">
                          {citation.title || citation.url}
                        </a>
                        {citation.snippet && (
                          <p className="snippet">{citation.snippet}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {answer.suggested_actions && answer.suggested_actions.length > 0 && (
                <div className="suggested-actions">
                  <h4>Suggested Actions:</h4>
                  <ul>
                    {answer.suggested_actions.map((action: string, idx: number) => (
                      <li key={idx}>{action}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="actions-section">
          <h2>Need More Help?</h2>
          <div className="action-buttons">
            <Link href="/cases" className="button primary">
              View My Cases
            </Link>
            <Link href="/cases/new" className="button secondary">
              Open a Request
            </Link>
          </div>
        </section>
      </main>

      <style jsx>{`
        .container {
          max-width: 800px;
          margin: 0 auto;
          padding: 2rem;
        }

        header {
          text-align: center;
          margin-bottom: 3rem;
        }

        header h1 {
          font-size: 2.5rem;
          margin-bottom: 0.5rem;
        }

        .ask-section {
          background: #f5f5f5;
          padding: 2rem;
          border-radius: 8px;
          margin-bottom: 2rem;
        }

        .ask-form {
          margin-top: 1rem;
        }

        .ask-form textarea {
          width: 100%;
          padding: 1rem;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 1rem;
          margin-bottom: 1rem;
        }

        .ask-form button {
          padding: 0.75rem 2rem;
          background: #0070f3;
          color: white;
          border: none;
          border-radius: 4px;
          font-size: 1rem;
          cursor: pointer;
        }

        .ask-form button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .answer-section {
          margin-top: 2rem;
          padding: 1.5rem;
          background: white;
          border-radius: 4px;
        }

        .answer h3 {
          margin-top: 0;
        }

        .citations {
          margin-top: 1.5rem;
          padding-top: 1.5rem;
          border-top: 1px solid #eee;
        }

        .citations ul {
          list-style: none;
          padding: 0;
        }

        .citations li {
          margin-bottom: 1rem;
        }

        .citations a {
          color: #0070f3;
          text-decoration: none;
        }

        .snippet {
          color: #666;
          font-size: 0.9rem;
          margin-top: 0.25rem;
        }

        .actions-section {
          text-align: center;
        }

        .action-buttons {
          display: flex;
          gap: 1rem;
          justify-content: center;
          margin-top: 1rem;
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

        .button.secondary {
          background: white;
          color: #0070f3;
          border: 2px solid #0070f3;
        }
      `}</style>
    </div>
  )
}

