import React, { useEffect, useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { apiClient } from '../../api/client'
import styles from './StudentDashboard.module.css'

interface AttendanceRecord {
  record_id: string
  student_code: string
  session_id: string
  course_name: string
  lecturer_code: string
  timestamp: string
  status: string
}

export function StudentDashboard() {
  const { user, logout } = useAuth()
  const [sessionCode, setSessionCode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [history, setHistory] = useState<AttendanceRecord[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)

  // Load attendance history
  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    setHistoryLoading(true)
    try {
      const response = await apiClient.getAttendanceHistory()
      setHistory(response.attendance || [])
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Failed to load attendance history' })
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleSubmitAttendance = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setMessage(null)

    try {
      await apiClient.submitAttendance({ session_code: sessionCode })
      setMessage({ type: 'success', text: 'Attendance submitted successfully!' })
      setSessionCode('')
      // Reload history
      loadHistory()
    } catch (err: any) {
      const errorText = err.message || 'Failed to submit attendance'
      setMessage({ type: 'error', text: errorText })
    } finally {
      setSubmitting(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Student Attendance Portal</h1>
        <div className={styles.userInfo}>
          <span>{user?.full_name}</span>
          <button onClick={logout} className={styles.logoutBtn}>
            Logout
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.card}>
          <h2>Submit Attendance</h2>
          <form onSubmit={handleSubmitAttendance} className={styles.form}>
            <div className={styles.formGroup}>
              <label htmlFor="sessionCode">Session Code</label>
              <input
                id="sessionCode"
                type="text"
                placeholder="Enter 10-character session code"
                value={sessionCode}
                onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
                maxLength={10}
                required
                disabled={submitting}
              />
            </div>

            {message && (
              <div className={`${styles.message} ${styles[message.type]}`}>
                {message.text}
              </div>
            )}

            <button
              type="submit"
              className={styles.submitBtn}
              disabled={submitting || !sessionCode.trim()}
            >
              {submitting ? 'Submitting...' : 'Submit Attendance'}
            </button>
          </form>
        </div>

        <div className={styles.card}>
          <h2>Your Attendance History</h2>
          {historyLoading ? (
            <div className={styles.loading}>Loading...</div>
          ) : history.length === 0 ? (
            <div className={styles.empty}>No attendance records found</div>
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Date &amp; Time</th>
                    <th>Course Name</th>
                    <th>Session Code</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((record) => (
                    <tr key={record.record_id}>
                      <td>{formatDate(record.timestamp)}</td>
                      <td>{record.course_name}</td>
                      <td>{record.session_id.substring(0, 8)}...</td>
                      <td>
                        <span className={`${styles.status} ${styles[record.status.toLowerCase()]}`}>
                          {record.status}
                        </span>
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
