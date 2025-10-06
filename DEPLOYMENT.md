# AI Receptionist Backend Deployment Guide

## 🏗️ Architecture Overview

This application consists of **3 main components**:

1. **FastAPI Server** - Main API server handling HTTP requests and WebSocket connections
2. **Celery Worker** - Background task processor for web scraping
3. **Redis** - Message broker and cache storage

## 🐳 Single Container Deployment

The application is configured to run all services in a **single container** using **Supervisor** for process management.

### Services Managed by Supervisor:
- **Redis Server** - Message broker and cache
- **Celery Worker** - Background task processor
- **FastAPI Server** - Main API server

## 📋 Deployment Steps

### 1. Environment Configuration

Create a `.env.production` file with the following variables:

```bash
ENV=production
AI_RECEPTION_SUPABASE_URL=your_supabase_url
AI_RECEPTION_SUPABASE_KEY=your_supabase_anon_key
AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
AI_RECEPTION_REDIS_URL=redis://localhost:6379/0
VAPI_WEBHOOK_SECRET=your_vapi_webhook_secret
VAPI_AUTH_TOKEN=your_vapi_auth_token
OPENAI_API_KEY=your_openai_api_key
```

### 2. Build and Deploy

The GitHub Actions workflow will automatically:
- Build the Docker image
- Push to Azure Container Registry
- Deploy to Azure Web App

### 3. Local Testing

To test locally with Docker Compose:

```bash
# Build and run all services
docker-compose up --build

# Check logs
docker-compose logs -f

# Test the API
curl http://localhost:8000/health
```

## 🔧 Process Management

Supervisor manages all processes with the following configuration:

- **Redis**: Runs on port 6379
- **Celery Worker**: Processes background tasks
- **FastAPI**: Runs on port 8000 with 2 workers

## 📊 Monitoring

- **Health Check**: `GET /health`
- **API Docs**: `GET /api/v1/docs`
- **Logs**: Available in `/var/log/supervisor/`

## 🚀 Production Considerations

1. **Redis Persistence**: Configured with AOF (Append Only File)
2. **Process Restart**: All services auto-restart on failure
3. **Logging**: Structured logging to supervisor log files
4. **Health Checks**: Built-in health check endpoint
5. **Security**: Non-root user for application processes

## 🔍 Troubleshooting

### Check Service Status
```bash
# Inside container
supervisorctl status

# View logs
tail -f /var/log/supervisor/fastapi.out.log
tail -f /var/log/supervisor/celery.out.log
tail -f /var/log/supervisor/redis.out.log
```

### Restart Services
```bash
# Restart specific service
supervisorctl restart fastapi
supervisorctl restart celery-worker
supervisorctl restart redis

# Restart all services
supervisorctl restart all
```
