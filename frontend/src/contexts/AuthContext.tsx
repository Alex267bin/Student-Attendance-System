import React, { createContext, useContext, useEffect, useState } from 'react'
import { apiClient } from '../api/client'

interface User {
  user_id: string
  username: string
  full_name: string
  email: string
  role: 'Student' | 'Lecturer' | 'Admin'
}

interface AuthContextType {
  user: User | null
  token: string | null
  loading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Initialize from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token')
    if (storedToken) {
      setToken(storedToken)
      apiClient.setToken(storedToken)
      checkAuth()
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (username: string, password: string) => {
    setError(null)
    setLoading(true)
    try {
      const response = await apiClient.login(username, password)
      const { token: newToken, user: newUser } = response
      apiClient.setToken(newToken)
      setToken(newToken)
      setUser(newUser)
    } catch (err: any) {
      const message = err.message || 'Login failed'
      setError(message)
      throw new Error(message)
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    apiClient.setToken(null)
    setToken(null)
    setUser(null)
    localStorage.removeItem('auth_token')
  }

  const checkAuth = async () => {
    try {
      const response = await apiClient.getMe()
      if (response.authenticated && response.user) {
        setUser(response.user)
      } else {
        logout()
      }
    } catch (_err) {
      logout()
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, error, login, logout, checkAuth }}>
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
