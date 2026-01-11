#!/bin/bash
set -e

# Configuration
DOCKER_USER="${DOCKER_USER:-gurkenkoenig}"
REPO_NAME="snout-pink"
TAG="${1:-latest}"
PLATFORM="linux/amd64,linux/arm64"

echo "Building and pushing Snout Pink images..."
echo "   Docker Hub: ${DOCKER_USER}/${REPO_NAME}"
echo "   Tag: ${TAG}"
echo "   Platforms: ${PLATFORM}"
echo ""

# Login check (check docker config for auth)
if ! grep -q "index.docker.io" ~/.docker/config.json 2>/dev/null; then
    echo "Not logged in to Docker Hub. Run: docker login"
    exit 1
fi

# Build and push backend (multi-platform)
echo "Building and pushing backend..."
docker buildx build --platform "${PLATFORM}" \
    -t "${DOCKER_USER}/${REPO_NAME}-backend:${TAG}" \
    --provenance=true \
    --sbom=true \
    --push ./backend

# Build and push frontend (multi-platform)
echo "Building and pushing frontend..."
docker buildx build --platform "${PLATFORM}" \
    -t "${DOCKER_USER}/${REPO_NAME}-frontend:${TAG}" \
    --provenance=true \
    --sbom=true \
    --push ./frontend

echo ""
echo "Done! Multi-arch images pushed (amd64 + arm64):"
echo "   ${DOCKER_USER}/${REPO_NAME}-backend:${TAG}"
echo "   ${DOCKER_USER}/${REPO_NAME}-frontend:${TAG}"
