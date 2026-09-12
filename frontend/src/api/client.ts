// API client for centralized requests
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

interface RequestOptions {
  method?: string
  headers?: Record<string, string>
  body?: unknown
}

class APIClient {
  private token: string | null = null

  setToken(token: string | null) {
    this.token = token
    if (token) {
      localStorage.setItem('auth_token', token)
    } else {
      localStorage.removeItem('auth_token')
    }
  }

  getToken(): string | null {
    return this.token || localStorage.getItem('auth_token')
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const config: RequestInit = {
      method: options.method || 'GET',
      headers,
    }

    if (options.body) {
      config.body = JSON.stringify(options.body)
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }))
      throw {
        status: response.status,
        message: error.error || error.message || 'Unknown error',
        data: error,
      }
    }

    if (response.status === 204) {
      return {} as T
    }

    return response.json()
  }

  // Auth endpoints
  async login(username: string, password: string) {
    return this.request<any>('/auth/login', {
      method: 'POST',
      body: { username, password },
    })
  }

  async getMe() {
    return this.request<any>('/auth/me')
  }

  // User endpoints
  async getUsers() {
    return this.request<any>('/users')
  }

  async createUser(data: Record<string, string>) {
    return this.request<any>('/users', {
      method: 'POST',
      body: data,
    })
  }

  async updateUser(userId: string, data: Record<string, string>) {
    return this.request<any>(`/users/${userId}`, {
      method: 'PUT',
      body: data,
    })
  }

  async deleteUser(userId: string) {
    return this.request<any>(`/users/${userId}`, {
      method: 'DELETE',
    })
  }

  // Session endpoints
  async createSession(data: Record<string, string>) {
    return this.request<any>('/sessions', {
      method: 'POST',
      body: data,
    })
  }

  async getSessions() {
    return this.request<any>('/sessions')
  }

  // Attendance endpoints
  async submitAttendance(data: Record<string, string>) {
    return this.request<any>('/attendance', {
      method: 'POST',
      body: data,
    })
  }

  async getAttendanceHistory() {
    return this.request<any>('/attendance/history')
  }

  // Report endpoints
  async getAttendanceReport(sessionId?: string) {
    const url = sessionId
      ? `/reports/attendance?session_id=${sessionId}`
      : '/reports/attendance'
    return this.request<any>(url)
  }
}

export const apiClient = new APIClient()
