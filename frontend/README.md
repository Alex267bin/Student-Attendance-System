# Student Attendance System - Frontend

A React + TypeScript frontend for the Student Attendance System, providing role-based dashboards for Students, Lecturers, and Administrators.

## Features

- **Authentication**: Login system with role-based access control
- **Student Dashboard**: Submit attendance and view attendance history
- **Lecturer Dashboard**: Create sessions, manage attendance, and view reports
- **Admin Dashboard**: User management system
- **Responsive Design**: Works on desktop and tablet devices
- **Secure API Integration**: Bearer token authentication with automatic expiration handling

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts                 # Centralized API client
│   ├── components/
│   │   └── ProtectedRoute.tsx        # Protected route component
│   ├── contexts/
│   │   └── AuthContext.tsx           # Authentication context
│   ├── pages/
│   │   ├── Login/                    # Login page
│   │   ├── Student/                  # Student dashboard
│   │   ├── Lecturer/                 # Lecturer dashboard
│   │   └── Admin/                    # Admin dashboard
│   ├── App.tsx                       # Main app component
│   └── main.tsx                      # Entry point
├── index.html                        # HTML template
├── package.json                      # Dependencies
├── tsconfig.json                     # TypeScript config
├── vite.config.ts                    # Vite config
├── .env.example                      # Environment template
└── README.md
```

## Setup

### Prerequisites

- Node.js 16+ and npm/yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create `.env.local` from `.env.example`:
```bash
cp .env.example .env.local
```

3. Configure the backend URL in `.env.local`:
```
VITE_API_BASE_URL=http://localhost:8000
```

## Development

Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Build

Build for production:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## API Integration

The frontend communicates with the backend through these main endpoints:

- **Authentication**: `POST /api/auth/login`, `GET /api/auth/me`
- **Users**: `GET/POST/PUT/DELETE /api/users/*` (Admin only)
- **Sessions**: `POST/GET /api/sessions` (Lecturer only)
- **Attendance**: `POST /api/attendance`, `GET /api/attendance/history` (Student)
- **Reports**: `GET /api/reports/attendance` (Lecturer)

See [Backend API Contract](../backend/api.py) for detailed specifications.

## Authentication Flow

1. User logs in with username and password
2. Backend returns access token
3. Token is stored in localStorage
4. Token is included in `Authorization: Bearer <token>` header for all requests
5. Token automatically expires after 30 minutes of inactivity
6. User is redirected to login on token expiration

## Role-Based Access

- **Student**: Can submit attendance and view personal attendance history
- **Lecturer**: Can create sessions, view attendance, and generate reports
- **Admin**: Can manage all users in the system

## Unsupported Figma Features

The following features from the Figma design are not implemented due to backend limitations:

- Password recovery (no backend endpoint available)
- Real-time WebSocket/SSE updates (backend doesn't support)
- Attendance status editing (no confirmed backend update endpoint)
- Semester filtering (no schema support in database)
- Admin statistics/activity widgets (limited backend support)

These features are marked as unavailable in the UI where applicable.

## Testing

All API endpoints are tested against the backend. Before deploying:

1. Ensure backend is running
2. Test login with different roles
3. Test each dashboard functionality
4. Verify attendance submission and history
5. Verify user management operations

## Deployment

The built frontend can be deployed to any static hosting:

- Build: `npm run build`
- Output directory: `dist/`
- Ensure backend URL is configured correctly in environment variables

## Development Notes

- Backend authentication uses 30-minute session timeout
- Session code format is 10 characters (URL-safe tokens)
- Status codes: Present, Late, Absent
- All dates/times are in ISO 8601 format
