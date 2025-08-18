#!/bin/bash

# AI Receptionist API - Development Startup Script

echo "🚀 Starting AI Receptionist API in development mode..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "📝 Please copy env.example to .env and configure your environment variables"
    echo "   cp env.example .env"
    echo ""
    echo "Required environment variables:"
    echo "  - AI_RECEPTION_SUPABASE_URL"
    echo "  - AI_RECEPTION_SUPABASE_KEY"
    echo "  - AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY"
    echo "  - AI_RECEPTION_SUPABASE_JWT_SECRET"
    echo "  - SECRET_KEY"
    echo ""
fi

# Start the development server
echo "🌐 Starting FastAPI development server..."
echo "📖 API Documentation will be available at: http://localhost:8000/api/v1/docs"
echo "🔍 ReDoc Documentation will be available at: http://localhost:8000/api/v1/redoc"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 