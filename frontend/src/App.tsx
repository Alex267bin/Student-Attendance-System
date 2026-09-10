import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginPage } from './pages/Login/Login'
import { StudentDashboard } from './pages/Student/StudentDashboard'
import { LecturerDashboard } from './pages/Lecturer/LecturerDashboard'
import { AdminDashboard } from './pages/Admin/AdminDashboard'

function DashboardRouter() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div>Loading authentication...</div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  // Route to the correct dashboard based on user role
  if (user.role === 'Student') {
    return <StudentDashboard />
  } else if (user.role === 'Lecturer') {
    return <LecturerDashboard />
  } else if (user.role === 'Admin') {
    return <AdminDashboard />
  }

  return <Navigate to="/login" replace />
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<DashboardRouter />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/unauthorized" element={
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              height: '100vh',
              flexDirection: 'column',
              gap: '20px'
            }}>
              <h1>Unauthorized</h1>
              <p>You do not have permission to access this page.</p>
              <a href="/login" style={{ color: '#667eea' }}>Go to Login</a>
            </div>
          } />
        </Routes>
      </AuthProvider>
    </Router>
  )
}

export default App
