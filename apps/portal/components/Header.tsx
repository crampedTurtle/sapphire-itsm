/**
 * Header component with user info and sign out
 */
import Link from 'next/link'
import { useAuth } from '../contexts/AuthContext'

export function Header() {
  const { email, isAuthenticated, signOut } = useAuth()

  if (!isAuthenticated) {
    return null
  }

  return (
    <header style={{
      background: '#fff',
      borderBottom: '1px solid #ddd',
      padding: '1rem 2rem',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
        <Link href="/" style={{ textDecoration: 'none', color: '#0070f3', fontWeight: 'bold' }}>
          Sapphire Support
        </Link>
        <nav style={{ display: 'flex', gap: '1rem' }}>
          <Link href="/cases" style={{ textDecoration: 'none', color: '#333' }}>
            My Cases
          </Link>
          <Link href="/cases/new" style={{ textDecoration: 'none', color: '#333' }}>
            New Case
          </Link>
        </nav>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <span style={{ fontSize: '0.875rem', color: '#666' }}>{email}</span>
        <button
          onClick={() => signOut()}
          style={{
            padding: '0.5rem 1rem',
            background: 'transparent',
            border: '1px solid #ddd',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.875rem'
          }}
        >
          Sign Out
        </button>
      </div>
    </header>
  )
}

