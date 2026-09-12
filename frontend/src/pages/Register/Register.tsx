import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../../api/client'
import styles from '../Login/Login.module.css'

export function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', username: '', password: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const updateField = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)
    try {
      await apiClient.register(form)
      setSuccess('Registration is completed successfully.')
      setTimeout(() => navigate('/login'), 700)
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.formWrapper}>
        <div className={styles.header}>
          <h1>Student Attendance System</h1>
          <p>Create Student Account</p>
        </div>
        <form onSubmit={handleSubmit} className={styles.form}>
          {(['name', 'email', 'username', 'password'] as const).map((field) => (
            <div className={styles.formGroup} key={field}>
              <label htmlFor={field}>{field === 'name' ? 'Name' : field[0].toUpperCase() + field.slice(1)}</label>
              <input
                id={field}
                type={field === 'password' ? 'password' : field === 'email' ? 'email' : 'text'}
                value={form[field]}
                onChange={(event) => updateField(field, event.target.value)}
                required
                disabled={loading}
              />
            </div>
          ))}
          {error && <div className={styles.error}>{error}</div>}
          {success && <div className={styles.success}>{success}</div>}
          <button type="submit" className={styles.submitBtn} disabled={loading}>
            {loading ? 'Creating Account...' : 'Submit'}
          </button>
          <div className={styles.helpText}>
            <p><a href="/login">Back to login</a></p>
          </div>
        </form>
      </div>
    </div>
  )
}
