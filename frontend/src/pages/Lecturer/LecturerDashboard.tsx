import React, { useEffect, useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { apiClient } from '../../api/client'
import styles from './LecturerDashboard.module.css'

interface Session {
  session_id: string
  course_name: string
  lecturer_code: string
  start_time: string
  end_time: string
  session_code: string
}

interface AttendanceRecord {
  session_id: string
  course_name: string
  lecturer_code: string
  student_code: string
  timestamp: string
  status: string
}

export function LecturerDashboard() {
  const { user, logout } = useAuth()
  const [sessions, setSessions] = useState<Session[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(true)
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([])
  const [attendanceLoading, setAttendanceLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState({
    course_name: '',
    start_time: '',
    end_time: '',
  })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    setSessionsLoading(true)
    try {
      const response = await apiClient.getSessions()
      setSessions(response.sessions || [])
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Failed to load sessions' })
    } finally {
      setSessionsLoading(false)
    }
  }

  const loadAttendance = async (sessionId: string) => {
    setAttendanceLoading(true)
    try {
      const response = await apiClient.getAttendanceReport(sessionId)
      setAttendance(response.attendance || [])
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Failed to load attendance data' })
    } finally {
      setAttendanceLoading(false)
    }
  }

  const handleSessionSelect = (sessionId: string) => {
    setSelectedSession(sessionId)
    loadAttendance(sessionId)
  }

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setMessage(null)

    try {
      const startDate = new Date(formData.start_time).toISOString()
      const endDate = new Date(formData.end_time).toISOString()

      await apiClient.createSession({
        course_name: formData.course_name,
        start_time: startDate,
        end_time: endDate,
      })

      setMessage({ type: 'success', text: 'Session created successfully!' })
      setFormData({ course_name: '', start_time: '', end_time: '' })
      setShowCreateForm(false)
      loadSessions()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to create session' })
    } finally {
      setSubmitting(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  const getSessionStatus = (session: Session) => {
    const now = new Date()
    const start = new Date(session.start_time)
    const end = new Date(session.end_time)

    if (now < start) return 'Upcoming'
    if (now > end) return 'Completed'
    return 'Active'
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Lecturer Attendance Dashboard</h1>
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
            <h2>Sessions</h2>
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className={styles.createBtn}
            >
              {showCreateForm ? 'Cancel' : 'Create Session'}
            </button>
          </div>

          {showCreateForm && (
            <form onSubmit={handleCreateSession} className={styles.form}>
              <div className={styles.formGroup}>
                <label htmlFor="courseName">Course Name</label>
                <input
                  id="courseName"
                  type="text"
                  placeholder="e.g., CS101 - Introduction to Programming"
                  value={formData.course_name}
                  onChange={(e) =>
                    setFormData({ ...formData, course_name: e.target.value })
                  }
                  required
                  disabled={submitting}
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label htmlFor="startTime">Start Time</label>
                  <input
                    id="startTime"
                    type="datetime-local"
                    value={formData.start_time}
                    onChange={(e) =>
                      setFormData({ ...formData, start_time: e.target.value })
                    }
                    required
                    disabled={submitting}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="endTime">End Time</label>
                  <input
                    id="endTime"
                    type="datetime-local"
                    value={formData.end_time}
                    onChange={(e) =>
                      setFormData({ ...formData, end_time: e.target.value })
                    }
                    required
                    disabled={submitting}
                  />
                </div>
              </div>

              <button
                type="submit"
                className={styles.submitBtn}
                disabled={submitting}
              >
                {submitting ? 'Creating...' : 'Create Session'}
              </button>
            </form>
          )}

          {sessionsLoading ? (
            <div className={styles.loading}>Loading sessions...</div>
          ) : sessions.length === 0 ? (
            <div className={styles.empty}>No sessions yet. Create one to get started!</div>
          ) : (
            <div className={styles.sessionsList}>
              {sessions.map((session) => (
                <div
                  key={session.session_id}
                  className={`${styles.sessionItem} ${
                    selectedSession === session.session_id ? styles.selected : ''
                  }`}
                  onClick={() => handleSessionSelect(session.session_id)}
                >
                  <div className={styles.sessionInfo}>
                    <h3>{session.course_name}</h3>
                    <p className={styles.sessionCode}>
                      Code: <span className={styles.code}>{session.session_code}</span>
                    </p>
                    <p className={styles.sessionTime}>
                      {formatDate(session.start_time)} to {formatDate(session.end_time)}
                    </p>
                    <span className={`${styles.status} ${styles[getSessionStatus(session).toLowerCase()]}`}>
                      {getSessionStatus(session)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {selectedSession && (
          <div className={styles.card}>
            <h2>Attendance for Selected Session</h2>
            {attendanceLoading ? (
              <div className={styles.loading}>Loading attendance...</div>
            ) : attendance.length === 0 ? (
              <div className={styles.empty}>No attendance records yet</div>
            ) : (
              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Student Code</th>
                      <th>Check-in Time</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attendance.map((record, idx) => (
                      <tr key={idx}>
                        <td>{record.student_code}</td>
                        <td>{formatDate(record.timestamp)}</td>
                        <td>
                          <span
                            className={`${styles.statusBadge} ${styles[record.status.toLowerCase()]}`}
                          >
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
        )}
      </main>
    </div>
  )
}
