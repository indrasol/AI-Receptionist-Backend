#!/bin/bash

# Set production environment
export ENV=production

# Start Redis in background
redis-server --port 6379 --bind 0.0.0.0 --daemonize yes

# Wait for Redis to start
sleep 2

# Start Celery worker in background
cd /src
celery -A app.celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

# Give Celery a moment to start
sleep 3

# Start FastAPI server (this will be the main process)
echo "Starting FastAPI server..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# If FastAPI exits, kill Celery
kill $CELERY_PID
