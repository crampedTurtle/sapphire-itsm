/**
 * Auth Guard component - protects routes that require authentication
 */
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { signIn, signUp, confirmSignUp, resendSignUpCode } from 'aws-amplify/auth'

interface AuthGuardProps {
  children: React.ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading, refreshAuth } = useAuth()
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmationCode, setConfirmationCode] = useState('')
  const [needsConfirmation, setNeedsConfirmation] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <div>Loading...</div>
      </div>
    )
  }

  // If Cognito is not configured, show a message
  if (!process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div>Cognito authentication is not configured.</div>
        <div style={{ fontSize: '0.875rem', color: '#666' }}>
          Please set NEXT_PUBLIC_COGNITO_USER_POOL_ID and NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID
        </div>
      </div>
    )
  }

  // Show login form if not authenticated
  if (!isAuthenticated) {
    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault()
      setError('')
      setLoading(true)

      try {
        if (needsConfirmation) {
          // Confirm sign up
          await confirmSignUp({
            username: email,
            confirmationCode: confirmationCode
          })
          setNeedsConfirmation(false)
          setError('')
          alert('Account confirmed! You can now sign in.')
        } else if (isSignUp) {
          // Sign up
          await signUp({
            username: email,
            password: password,
            options: {
              userAttributes: {
                email: email
              }
            }
          })
          setNeedsConfirmation(true)
          setError('')
        } else {
          // Sign in
          await signIn({
            username: email,
            password: password
          })
          await refreshAuth()
        }
      } catch (err: any) {
        setError(err.message || 'An error occurred')
        console.error('Auth error:', err)
      } finally {
        setLoading(false)
      }
    }

    const handleResendCode = async () => {
      try {
        await resendSignUpCode({ username: email })
        alert('Confirmation code resent to your email')
      } catch (err: any) {
        setError(err.message || 'Failed to resend code')
      }
    }

    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        padding: '2rem',
        background: '#f5f5f5'
      }}>
        <div style={{
          background: 'white',
          padding: '2rem',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          width: '100%',
          maxWidth: '400px'
        }}>
          <h1 style={{ marginTop: 0, marginBottom: '1.5rem', textAlign: 'center' }}>
            {needsConfirmation ? 'Confirm Account' : isSignUp ? 'Sign Up' : 'Sign In'}
          </h1>
          
          <form onSubmit={handleSubmit}>
            {error && (
              <div style={{
                background: '#fee',
                color: '#c33',
                padding: '0.75rem',
                borderRadius: '4px',
                marginBottom: '1rem',
                fontSize: '0.875rem'
              }}>
                {error}
              </div>
            )}

            {needsConfirmation ? (
              <>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                    Confirmation Code
                  </label>
                  <input
                    type="text"
                    value={confirmationCode}
                    onChange={(e) => setConfirmationCode(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '1rem'
                    }}
                    placeholder="Enter code from email"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: '#0070f3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '1rem',
                    fontWeight: '500',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                    marginBottom: '0.5rem'
                  }}
                >
                  {loading ? 'Confirming...' : 'Confirm'}
                </button>
                <button
                  type="button"
                  onClick={handleResendCode}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: 'transparent',
                    color: '#0070f3',
                    border: '1px solid #0070f3',
                    borderRadius: '4px',
                    fontSize: '0.875rem',
                    cursor: 'pointer'
                  }}
                >
                  Resend Code
                </button>
              </>
            ) : (
              <>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '1rem'
                    }}
                    placeholder="your@email.com"
                  />
                </div>
                <div style={{ marginBottom: '1.5rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '1rem'
                    }}
                    placeholder="••••••••"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: '#0070f3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '1rem',
                    fontWeight: '500',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                    marginBottom: '0.5rem'
                  }}
                >
                  {loading ? (isSignUp ? 'Signing up...' : 'Signing in...') : (isSignUp ? 'Sign Up' : 'Sign In')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsSignUp(!isSignUp)
                    setError('')
                  }}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    background: 'transparent',
                    color: '#666',
                    border: 'none',
                    fontSize: '0.875rem',
                    cursor: 'pointer',
                    textDecoration: 'underline'
                  }}
                >
                  {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
                </button>
              </>
            )}
          </form>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

