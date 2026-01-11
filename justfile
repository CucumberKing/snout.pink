# Default recipe
default:
    @just --list

# ─────────────────────────────────────────────────────────────────────────────
# Development
# ─────────────────────────────────────────────────────────────────────────────

# Start the FastAPI backend
backend:
    cd backend && uv run uvicorn main:app --reload --app-dir src --no-access-log

# Start the Angular frontend
frontend:
    cd frontend && npm start

# Start local MongoDB with Docker
start_local_mongo:
    docker run -d --name snout-mongo -p 27017:27017 mongo:latest

# Stop local MongoDB
stop_local_mongo:
    docker stop snout-mongo && docker rm snout-mongo

# ─────────────────────────────────────────────────────────────────────────────
# Production
# ─────────────────────────────────────────────────────────────────────────────

# Build Docker containers
build:
    sh build.sh
