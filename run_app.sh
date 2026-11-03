#!/usr/bin/env bash
# ==============================================================================
# AI Interviewer - Unified Single-Command Local Launcher (2026 Edition)
# Launches both FastAPI Backend (port 8000) and Next.js Frontend (port 3000)
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=========================================================="
echo "  🚀 Starting AI Interviewer (2026 Multimodal Platform)"
echo "=========================================================="

# Check Python environment
if [ -d "backend/.venv" ]; then
    PYTHON_CMD="backend/.venv/bin/python"
    UVICORN_CMD="backend/.venv/bin/uvicorn"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
    UVICORN_CMD="uvicorn"
else
    echo "❌ Error: Python 3 not found."
    exit 1
fi

# Ensure data directory exists
mkdir -p backend/data

# Function to stop background processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down AI Interviewer services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start FastAPI Backend
echo "📦 Starting FastAPI backend on http://127.0.0.1:8000 ..."
(cd backend && $UVICORN_CMD app.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

# Wait for backend health check
echo "⏳ Verifying backend health..."
for i in {1..20}; do
    if curl -s http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
        echo "✅ Backend is healthy and ready!"
        break
    fi
    sleep 0.5
done

# 2. Start Next.js Frontend
echo "💻 Starting Next.js frontend on http://127.0.0.1:3000 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo "  🎉 AI Interviewer is Live!"
echo "  👉 Open your browser: http://localhost:3000"
echo "  👉 Backend API Docs:  http://localhost:8000/docs"
echo "  Press Ctrl+C to stop all services."
echo "=========================================================="

wait
