/**
 * Authentication context for Cognito
 * Provides user authentication state and methods throughout the app
 */
import React, { createContext, useContext, useEffect, useState } from 'react'
import { getCurrentUser, signOut, fetchAuthSession, fetchUserAttributes } from 'aws-amplify/auth'
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
      
      // Get user attributes including email
      try {
        const attributes = await fetchUserAttributes()
        const userEmail = attributes.email || attributes['custom:email'] || currentUser.username || null
        setEmail(userEmail)
        
        // Get tenant_id from custom attribute if available
        const tenantIdAttr = attributes['custom:tenant_id'] || null
        setTenantId(tenantIdAttr)
      } catch (err) {
        // Fallback to username if attributes can't be fetched
        console.error('Error fetching user attributes:', err)
        setEmail(currentUser.username || null)
        setTenantId(null)
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

