/**
 * Auth Guard component - protects routes that require authentication
 */
import { useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAuth } from '../contexts/AuthContext'
import { Authenticator } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'

interface AuthGuardProps {
  children: React.ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()

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

  // Show Amplify Authenticator if not authenticated
  if (!isAuthenticated) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        padding: '2rem'
      }}>
        <Authenticator
          loginMechanisms={['email']}
          signUpAttributes={['email']}
        >
          {({ signOut, user }) => (
            <div>
              {children}
            </div>
          )}
        </Authenticator>
      </div>
    )
  }

  return <>{children}</>
}

