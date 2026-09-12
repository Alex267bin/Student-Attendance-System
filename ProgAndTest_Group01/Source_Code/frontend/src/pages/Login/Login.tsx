import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import styles from './Login.module.css'

type Role = 'Student' | 'Lecturer' | 'Admin'

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [role, setRole] = useState<Role>('Student')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      // Redirect based on role - user's actual role from backend will determine this
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.formWrapper}>
        <div className={styles.logo}>U</div>
        <div className={styles.header}>
          <h1>Student Attendance System</h1>
          <p>Please sign in to access your portal</p>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          {error && <div className={styles.error}><span aria-hidden="true">!</span>{error}</div>}
          <div className={styles.roleSelector}>
            <label>Sign In As</label>
            <div className={styles.roleTabs} role="tablist" aria-label="Sign in role">
              {(['Student', 'Lecturer', 'Admin'] as Role[]).map((option) => (
                <button
                  key={option}
                  type="button"
                  className={role === option ? styles.activeRole : ''}
                  onClick={() => setRole(option)}
                  role="tab"
                  aria-selected={role === option}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="username">Username or Academic Email</label>
            <input
              id="username"
              type="text"
              placeholder="Enter your username or email"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password">Password</label>
            <div className={styles.passwordInput}>
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className={styles.togglePassword}
                disabled={loading}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <div className={styles.formOptions}>
            <label className={styles.rememberMe} htmlFor="remember">
              <input type="checkbox" id="remember" />
              <span>Remember me</span>
            </label>
            <button type="button" className={styles.forgotPassword}>Forgot Password?</button>
          </div>

          <button type="submit" className={styles.submitBtn} disabled={loading}>
            {loading ? 'Signing In...' : 'Sign In'}
          </button>

        </form>
      </div>
    </div>
  )
}
