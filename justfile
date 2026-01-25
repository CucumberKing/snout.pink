# Default recipe
default:
    @just --list

# ═══════════════════════════════════════════════════════════════════════════════
# Docker: Build & Push (GHCR)
# ═══════════════════════════════════════════════════════════════════════════════

# GitHub Container Registry
REGISTRY := "ghcr.io/cucumberking/snout.pink"

# Build and push all containers
build-docker: build-docker-backend build-docker-frontend
    @echo "All images built and pushed successfully!"

# Build and push backend image
build-docker-backend:
    docker buildx build \
        --platform linux/amd64 \
        --tag {{REGISTRY}}-backend:latest \
        --push \
        ./backend

# Build and push frontend image
build-docker-frontend:
    docker buildx build \
        --platform linux/amd64 \
        --tag {{REGISTRY}}-frontend:latest \
        --push \
        ./frontend

# Setup buildx builder (run once)
docker-setup-buildx:
    docker buildx create --name multiarch --driver docker-container --use || docker buildx use multiarch
    docker buildx inspect --bootstrap

# Login to GHCR (uses gh CLI - no manual token needed!)
docker-login:
    gh auth token | docker login ghcr.io -u $(gh api user --jq .login) --password-stdin

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

