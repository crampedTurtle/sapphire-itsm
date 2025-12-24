/**
 * Authentication context for Cognito
 * Provides user authentication state and methods throughout the app
 */
import React, { createContext, useContext, useEffect, useState } from 'react'
import { getCurrentUser, signOut, fetchAuthSession } from 'aws-amplify/auth'
import type { AuthUser } from 'aws-amplify/auth'

interface AuthContextType {
  user: AuthUser | null
  email: string | null
  tenantId: string | null
  isLoading: boolean
  isAuthenticated: boolean
  signOut: () => Promise<void>
  refreshAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [email, setEmail] = useState<string | null>(null)
  const [tenantId, setTenantId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadUser = async () => {
    try {
      const currentUser = await getCurrentUser()
      setUser(currentUser)
      
      // Get email from user attributes
      const emailAttr = currentUser.signInDetails?.loginId || 
                       currentUser.username ||
                       null
      setEmail(emailAttr)
      
      // Get tenant_id from custom attribute if available
      // Cognito custom attributes are prefixed with 'custom:'
      // You can set this during user registration or via Admin API
      try {
        const session = await fetchAuthSession()
        // Note: Custom attributes require AdminGetUser API call
        // For now, we'll resolve tenant from email domain on the backend
        setTenantId(null) // Will be resolved from email domain
      } catch (err) {
        console.error('Error fetching session:', err)
      }
    } catch (err) {
      // User is not authenticated
      setUser(null)
      setEmail(null)
      setTenantId(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadUser()
  }, [])

  const handleSignOut = async () => {
    try {
      await signOut()
      setUser(null)
      setEmail(null)
      setTenantId(null)
    } catch (err) {
      console.error('Error signing out:', err)
      throw err
    }
  }

  const refreshAuth = async () => {
    setIsLoading(true)
    await loadUser()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        email,
        tenantId,
        isLoading,
        isAuthenticated: !!user,
        signOut: handleSignOut,
        refreshAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

