#!/bin/bash

# Set production environment
export ENV=production

# Start Redis in background with memory overcommit warning suppression
redis-server --port 6379 --bind 0.0.0.0 --daemonize yes --save "" --appendonly no

# Wait for Redis to start
sleep 2

# Start Celery worker in background with non-root user
cd /src
celery -A app.celery_app worker --loglevel=info --concurrency=2 --uid=1000 --gid=1000 &
CELERY_PID=$!

# Start FastAPI server (this will be the main process)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# If FastAPI exits, kill Celery
kill $CELERY_PID
