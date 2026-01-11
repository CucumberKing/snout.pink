# syntax=docker/dockerfile:1
# Backend Dockerfile using uv with Python 3.14

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

# Update system packages to fix vulnerabilities and create non-root user
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Copy dependency files first (better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies with caching (as root for package installation)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

# Copy application code
COPY src/ src/

# Sync the project (installs the app itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uv (uses the .venv automatically)
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
