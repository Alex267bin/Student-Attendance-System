import React, { useEffect, useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { apiClient } from '../../api/client'
import styles from './AdminDashboard.module.css'

interface User {
  user_id: string
  username: string
  full_name: string
  email: string
  role: string
}

type UserRole = 'Student' | 'Lecturer' | 'Admin'

export function AdminDashboard() {
  const { user, logout } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    full_name: '',
    email: '',
    role: 'Student' as UserRole,
    student_code: '',
    class_id: '',
    lecturer_code: '',
    department: '',
  })

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    setLoading(true)
    try {
      const response = await apiClient.getUsers()
      setUsers(response.users || [])
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Failed to load users' })
    } finally {
      setLoading(false)
    }
  }

  const handleAddUser = () => {
    setEditingUser(null)
    setFormData({
      username: '',
      password: '',
      full_name: '',
      email: '',
      role: 'Student',
      student_code: '',
      class_id: '',
      lecturer_code: '',
      department: '',
    })
    setShowCreateForm(true)
  }

  const handleEditUser = (u: User) => {
    setEditingUser(u)
    setFormData({
      username: u.username,
      password: '',
      full_name: u.full_name,
      email: u.email,
      role: u.role as UserRole,
      student_code: '',
      class_id: '',
      lecturer_code: '',
      department: '',
    })
    setShowCreateForm(true)
  }

  const handleSubmitForm = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setMessage(null)

    try {
      const payload: Record<string, string> = {
        username: formData.username,
        full_name: formData.full_name,
        email: formData.email,
        role: formData.role,
      }

      if (formData.password) {
        payload.password = formData.password
      }

      if (formData.role === 'Student') {
        payload.student_code = formData.student_code
        payload.class_id = formData.class_id
      } else if (formData.role === 'Lecturer') {
        payload.lecturer_code = formData.lecturer_code
        payload.department = formData.department
      }

      if (editingUser) {
        await apiClient.updateUser(editingUser.user_id, payload)
        setMessage({ type: 'success', text: 'User updated successfully!' })
      } else {
        // For create, password is required
        if (!formData.password) {
          throw new Error('Password is required for new users')
        }
        await apiClient.createUser(payload)
        setMessage({ type: 'success', text: 'User created successfully!' })
      }

      setShowCreateForm(false)
      loadUsers()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Operation failed' })
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteUser = async (userId: string) => {
    if (confirm('Are you sure you want to delete this user?')) {
      try {
        await apiClient.deleteUser(userId)
        setMessage({ type: 'success', text: 'User deleted successfully!' })
        loadUsers()
      } catch (err: any) {
        setMessage({ type: 'error', text: err.message || 'Failed to delete user' })
      }
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Admin Dashboard</h1>
        <div className={styles.userInfo}>
          <span>{user?.full_name}</span>
          <button onClick={logout} className={styles.logoutBtn}>
            Logout
          </button>
        </div>
      </header>

      <main className={styles.main}>
        {message && (
          <div className={`${styles.message} ${styles[message.type]}`}>
            {message.text}
          </div>
        )}

        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <h2>User Management</h2>
            <button
              onClick={handleAddUser}
              className={styles.createBtn}
              disabled={showCreateForm}
            >
              Add User
            </button>
          </div>

          {showCreateForm && (
            <form onSubmit={handleSubmitForm} className={styles.form}>
              <h3>{editingUser ? 'Edit User' : 'Create New User'}</h3>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label htmlFor="username">Username</label>
                  <input
                    id="username"
                    type="text"
                    value={formData.username}
                    onChange={(e) =>
                      setFormData({ ...formData, username: e.target.value })
                    }
                    required
                    disabled={submitting}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="email">Email</label>
                  <input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) =>
                      setFormData({ ...formData, email: e.target.value })
                    }
                    required
                    disabled={submitting}
                  />
                </div>
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label htmlFor="fullName">Full Name</label>
                  <input
                    id="fullName"
                    type="text"
                    value={formData.full_name}
                    onChange={(e) =>
                      setFormData({ ...formData, full_name: e.target.value })
                    }
                    required
                    disabled={submitting}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="role">Role</label>
                  <select
                    id="role"
                    value={formData.role}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        role: e.target.value as UserRole,
                      })
                    }
                    disabled={submitting}
                  >
                    <option value="Student">Student</option>
                    <option value="Lecturer">Lecturer</option>
                    <option value="Admin">Admin</option>
                  </select>
                </div>
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="password">
                  Password {editingUser ? '(leave blank to keep current)' : '(required)'}
                </label>
                <input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  required={!editingUser}
                  disabled={submitting}
                />
              </div>

              {formData.role === 'Student' && (
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label htmlFor="studentCode">Student Code</label>
                    <input
                      id="studentCode"
                      type="text"
                      value={formData.student_code}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          student_code: e.target.value,
                        })
                      }
                      required={formData.role === 'Student' && !editingUser}
                      disabled={submitting}
                    />
                  </div>

                  <div className={styles.formGroup}>
                    <label htmlFor="classId">Class ID</label>
                    <input
                      id="classId"
                      type="text"
                      value={formData.class_id}
                      onChange={(e) =>
                        setFormData({ ...formData, class_id: e.target.value })
                      }
                      required={formData.role === 'Student' && !editingUser}
                      disabled={submitting}
                    />
                  </div>
                </div>
              )}

              {formData.role === 'Lecturer' && (
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label htmlFor="lecturerCode">Lecturer Code</label>
                    <input
                      id="lecturerCode"
                      type="text"
                      value={formData.lecturer_code}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          lecturer_code: e.target.value,
                        })
                      }
                      required={formData.role === 'Lecturer' && !editingUser}
                      disabled={submitting}
                    />
                  </div>

                  <div className={styles.formGroup}>
                    <label htmlFor="department">Department</label>
                    <input
                      id="department"
                      type="text"
                      value={formData.department}
                      onChange={(e) =>
                        setFormData({ ...formData, department: e.target.value })
                      }
                      required={formData.role === 'Lecturer' && !editingUser}
                      disabled={submitting}
                    />
                  </div>
                </div>
              )}

              <div className={styles.formActions}>
                <button
                  type="submit"
                  className={styles.submitBtn}
                  disabled={submitting}
                >
                  {submitting ? 'Saving...' : 'Save User'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className={styles.cancelBtn}
                  disabled={submitting}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {loading ? (
            <div className={styles.loading}>Loading users...</div>
          ) : users.length === 0 ? (
            <div className={styles.empty}>No users found</div>
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Full Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.user_id}>
                      <td>{u.username}</td>
                      <td>{u.full_name}</td>
                      <td>{u.email}</td>
                      <td>
                        <span className={`${styles.role} ${styles[u.role.toLowerCase()]}`}>
                          {u.role}
                        </span>
                      </td>
                      <td>
                        <div className={styles.actions}>
                          <button
                            onClick={() => handleEditUser(u)}
                            className={styles.editBtn}
                            disabled={showCreateForm}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteUser(u.user_id)}
                            className={styles.deleteBtn}
                            disabled={showCreateForm}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
