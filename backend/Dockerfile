FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend
COPY migrations ./migrations

ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/attendance.db

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "backend.api"]
