## Verified in this workspace

- Backend API suite: `python -m unittest discover -s tests -v`
- Source/configuration inspection: backend, frontend, SQLite migration, Dockerfiles, Compose file, and environment template
- Docker architecture inspection: frontend container proxies `/api` to the backend service; backend persists SQLite in the `attendance_data` volume
- Docker image build: `docker compose build` completed successfully
- Docker runtime: backend healthy and frontend running via `docker compose up -d`
- HTTP integration: `http://localhost:8000/api/auth/me`, `http://localhost:5173/`, and `http://localhost:5173/api/auth/me` returned HTTP 200
- Container logs: backend served API requests and Nginx served the frontend and proxied API request

## Docker evidence to collect on a machine with Docker Desktop

Run from the repository root and retain the terminal output or screenshots showing the actual project:

```sh
docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose logs --tail=100
```

Then open `http://localhost:5173`, exercise login and the role dashboard, and capture the browser plus `docker compose ps` output. The API is routed through the frontend at `/api`; the backend persists SQLite data in the `attendance_data` volume.

The checks above were run with Docker Desktop and are based on actual command output. Retain terminal output or screenshots from the commands below if visual evidence is required for submission. Do not replace this with fabricated screenshots.
