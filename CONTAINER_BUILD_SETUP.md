# Container Build Setup Guide

Template für GHCR-basierte Container-Builds mit GitHub Actions.

---

## Übersicht

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Entwickler    │────▶│   GitHub Repo   │────▶│      GHCR       │
│                 │     │                 │     │                 │
│ just build-*    │     │ Push main/tag   │     │ ghcr.io/owner/  │
│ (manuell)       │     │ → GH Actions    │     │ repo-service    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**Komponenten:**
- **justfile**: Lokale Build-Commands
- **GitHub Actions**: Automatische Builds bei Push auf `main` oder Tag
- **GHCR**: GitHub Container Registry als Image-Speicher
- **gh CLI**: Authentifizierung ohne manuelle Token-Verwaltung

---

## 1. Naming Convention

### Image-Namen
```
ghcr.io/{owner}/{repo}-{service}:{tag}
```

**Beispiele:**
- `ghcr.io/cucumberking/hackernews.pink-backend:latest`
- `ghcr.io/cucumberking/myproject-api:2026.001`

### Tags
| Tag | Wann | Beschreibung |
|-----|------|--------------|
| `latest` | Jeder Build | Rolling tag |
| `2026.001` | Git Tag Push | Release-Version |

---

## 2. Justfile Setup

### Variablen anpassen
```just
# GitHub Container Registry - ANPASSEN!
REGISTRY := "ghcr.io/{owner}/{repo}"
```

### Build Commands Template
```just
# ═══════════════════════════════════════════════════════════════════════════════
# Docker: Build & Push (GHCR)
# ═══════════════════════════════════════════════════════════════════════════════

# GitHub Container Registry
REGISTRY := "ghcr.io/OWNER/REPO"

# Build and push all containers
build-docker: build-docker-service1 build-docker-service2
    @echo "All images built and pushed successfully!"

# Build and push service1 image
# Für Services mit shared package: Context = ".", Dockerfile = "./service/Dockerfile"
build-docker-service1:
    docker buildx build \
        --platform linux/amd64 \
        --tag {{REGISTRY}}-service1:latest \
        --push \
        -f ./service1/Dockerfile \
        .

# Build and push service2 image (standalone, z.B. Frontend)
# Für standalone Services: Context = "./service"
build-docker-service2:
    docker buildx build \
        --platform linux/amd64 \
        --tag {{REGISTRY}}-service2:latest \
        --push \
        ./service2

# Setup buildx builder (run once)
docker-setup-buildx:
    docker buildx create --name multiarch --driver docker-container --use || docker buildx use multiarch
    docker buildx inspect --bootstrap

# Login to GHCR (uses gh CLI - no manual token needed!)
docker-login:
    gh auth token | docker login ghcr.io -u $(gh api user --jq .login) --password-stdin
```

### Build Context Regeln

| Service-Typ | Context | Dockerfile | Beispiel |
|-------------|---------|------------|----------|
| Mit shared package | `.` (Repo root) | `./service/Dockerfile` | Backend, API |
| Standalone | `./service` | `./service/Dockerfile` | Frontend |

---

## 3. Dockerfile Setup

### LABEL für Repo-Verknüpfung (WICHTIG!)

Jedes Dockerfile braucht dieses Label für automatische GHCR-Repo-Verknüpfung:

```dockerfile
FROM base-image AS production

LABEL org.opencontainers.image.source=https://github.com/OWNER/REPO

# ... rest of Dockerfile
```

**Platzierung:** Nach dem `FROM` der finalen Stage (bei Multi-Stage Builds).

### Python Service Template (Multi-Stage mit uv)

```dockerfile
# Service Dockerfile
# Built from repository root for shared package access

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1: Build
# ═══════════════════════════════════════════════════════════════════════════════
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy shared package (if exists)
COPY shared ./shared

# Copy service package
COPY service/pyproject.toml service/uv.lock ./service/
COPY service/src ./service/src

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    cd service && uv sync --frozen --no-dev

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: Production
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.14-slim-bookworm AS production

LABEL org.opencontainers.image.source=https://github.com/OWNER/REPO

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# Copy from builder
COPY --from=builder --chown=appuser:appuser /app/service/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/service/src ./src
COPY --from=builder --chown=appuser:appuser /app/shared ./shared

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src:/app/shared/src
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Template (Node + Nginx)

```dockerfile
# Frontend Dockerfile

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1: Build
# ═══════════════════════════════════════════════════════════════════════════════
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: Production
# ═══════════════════════════════════════════════════════════════════════════════
FROM nginx:alpine AS production

LABEL org.opencontainers.image.source=https://github.com/OWNER/REPO

RUN apk add --no-cache curl

# Configure nginx for non-root
RUN rm /etc/nginx/conf.d/default.conf && \
    sed -i 's|/var/run/nginx.pid|/tmp/nginx.pid|g' /etc/nginx/nginx.conf && \
    sed -i 's|user  nginx;|#user  nginx;|g' /etc/nginx/nginx.conf

# Create non-root user
RUN addgroup -g 1001 -S frontend && \
    adduser -u 1001 -S frontend -G frontend

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist/OUTPUT_DIR /usr/share/nginx/html

RUN chown -R frontend:frontend /usr/share/nginx/html && \
    chown -R frontend:frontend /var/cache/nginx && \
    chown -R frontend:frontend /var/log/nginx && \
    touch /var/run/nginx.pid && chown frontend:frontend /var/run/nginx.pid

USER frontend

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

---

## 4. GitHub Actions Workflow

Erstelle `.github/workflows/docker.yml`:

```yaml
name: Docker Build

on:
  push:
    branches: [main]
    tags: ['*']

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        service: [service1, service2, service3]  # ANPASSEN!
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Determine tags
        id: tags
        run: |
          # ANPASSEN: repo-name
          IMAGE="ghcr.io/${{ github.repository_owner }}/REPO-NAME-${{ matrix.service }}"
          if [[ "${{ github.ref_type }}" == "tag" ]]; then
            echo "tags=${IMAGE}:${{ github.ref_name }},${IMAGE}:latest" >> $GITHUB_OUTPUT
          else
            echo "tags=${IMAGE}:latest" >> $GITHUB_OUTPUT
          fi

      - name: Build and push
        run: |
          # ANPASSEN: standalone services (z.B. frontend)
          CONTEXT="${{ matrix.service == 'frontend' && './frontend' || '.' }}"
          docker buildx build \
            --platform linux/amd64 \
            $(echo "${{ steps.tags.outputs.tags }}" | sed 's/,/ --tag /g' | sed 's/^/--tag /') \
            --push \
            -f ./${{ matrix.service }}/Dockerfile \
            "${CONTEXT}"
```

---

## 5. Erstmaliges Setup

### Voraussetzungen
- Docker Desktop mit buildx
- GitHub CLI (`gh`) installiert und eingeloggt
- Repository auf GitHub

### Schritte

1. **gh CLI Scope hinzufügen** (einmalig):
   ```bash
   gh auth refresh -s write:packages
   ```

2. **Buildx Setup** (einmalig):
   ```bash
   just docker-setup-buildx
   ```

3. **GHCR Login**:
   ```bash
   just docker-login
   ```

4. **Erster Build**:
   ```bash
   just build-docker-service1
   ```

5. **Package mit Repo verknüpfen** (einmalig pro Package):
   - Gehe zu `https://github.com/users/OWNER/packages/container/REPO-SERVICE/settings`
   - "Connect Repository" klicken
   - Repository auswählen

---

## 6. Tägliche Nutzung

### Lokaler Build + Push
```bash
just docker-login          # Falls Session abgelaufen
just build-docker          # Alle Services
just build-docker-backend  # Einzelner Service
```

### Release erstellen
```bash
git tag 2026.001
git push origin 2026.001
# → GitHub Actions buildet automatisch mit :2026.001 und :latest
```

### Automatische Builds
- Push auf `main` → Alle Services mit `:latest`
- Push Tag → Alle Services mit `:tag` und `:latest`

---

## 7. Checkliste für neues Projekt

- [ ] `justfile` kopieren und REGISTRY anpassen
- [ ] `.github/workflows/docker.yml` kopieren und anpassen:
  - [ ] Service-Matrix
  - [ ] Repo-Name im Image-Pfad
  - [ ] Standalone-Services im Context-Check
- [ ] Dockerfiles mit `LABEL org.opencontainers.image.source` versehen
- [ ] `gh auth refresh -s write:packages` ausführen
- [ ] `just docker-setup-buildx` ausführen
- [ ] Ersten Build machen: `just build-docker`
- [ ] Packages manuell mit Repo verknüpfen (einmalig)

---

## 8. Troubleshooting

### "permission_denied: The token provided does not match expected scopes"
```bash
gh auth refresh -s write:packages
docker logout ghcr.io
just docker-login
```

### "no matching manifest for linux/arm64"
Das Image ist nur für amd64 gebaut. Für lokales Testen auf ARM-Mac:
```bash
docker pull --platform linux/amd64 IMAGE:TAG
```

### Package nicht mit Repo verknüpft
1. Gehe zu Package Settings auf GitHub
2. "Connect Repository" klicken
3. Nach erstem Push mit LABEL wird es automatisch verknüpft

### Build cached aber Änderungen nicht sichtbar
```bash
docker buildx build --no-cache ...
```
