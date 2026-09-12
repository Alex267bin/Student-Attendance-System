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
      await loadHistory()
    } catch (err: any) {
      const errorText = err.status === 404 || err.status === 400
        ? 'Session not found or no longer active.'
        : err.message || 'Failed to submit attendance'
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
        <div className={styles.brand}>
          <div className={styles.logo}>U</div>
          <div><strong>UTH University</strong><span>{user?.student_code || 'Student'}</span></div>
        </div>
        <div className={styles.userInfo}>
          <span className={styles.notification} aria-label="Notifications">&#9675;</span>
          <div className={styles.identity}><strong>{user?.full_name}</strong><span>Student</span></div>
          <div className={styles.avatar}>{user?.full_name?.charAt(0).toUpperCase()}</div>
          <button onClick={logout} className={styles.logoutBtn}>
            Log out
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.card}>
          <div className={styles.cardIntro}>
            <h2>Submit Live Attendance</h2>
            <p>Enter the session code displayed by your lecturer or scan their QR code to register your check-in.</p>
          </div>
          <form onSubmit={handleSubmitAttendance} className={styles.form}>
            <div className={styles.formGroup}>
              <label htmlFor="sessionCode">Session Code</label>
              <div className={styles.codeInputWrap}>
                <input
                  id="sessionCode"
                  type="text"
                  placeholder="Enter session code"
                  value={sessionCode}
                  onChange={(e) => setSessionCode(e.target.value)}
                  maxLength={10}
                  required
                  disabled={submitting}
                />
              </div>
            </div>

            {message && (
              <div className={`${styles.message} ${styles[message.type]}`}>
                {message.text}
              </div>
            )}

            <div className={styles.formActions}>
              <button type="submit" className={styles.submitBtn} disabled={submitting || !sessionCode.trim()}>
                {submitting ? 'Submitting...' : 'Submit Code'}
              </button>
              <button type="button" className={styles.secondaryBtn} disabled>Scan QR Code</button>
            </div>
          </form>
        </div>

        <div className={styles.card}>
          <div className={styles.historyHeader}>
            <div><h2>Attendance History</h2><p>Your recent attendance records.</p></div>
            <div className={styles.filters}><select aria-label="Course filter"><option>All courses</option></select></div>
          </div>
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
                    <th>Lecturer</th>
                    <th>Session Code</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((record) => (
                    <tr key={record.record_id}>
                      <td>{formatDate(record.timestamp)}</td>
                      <td>{record.course_name}</td>
                      <td>{record.lecturer_code}</td>
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
