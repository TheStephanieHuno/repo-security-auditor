# Repo Security Auditor

A security auditing tool that analyzes GitHub repositories for:

- Source-code vulnerabilities
- Exposed secrets
- Vulnerable dependencies
- Insecure configurations

## Tech Stack

- Frontend: Next.js + TypeScript
- Backend: Python + FastAPI
- Database: PostgreSQL 16
- Cache/Queue: Redis
- Background Jobs: arq (Redis-backed scan worker)
- Containerization: Docker
- CI/CD: GitHub Actions

## Project layout

```text
backend_app_test/      FastAPI backend (API, scanners, arq worker) — run by Docker
Dockerfile             API image          Dockerfile.worker   scan-worker image
docker-compose.yml     PostgreSQL, Redis, API (:8000), scan worker
frontend/              Next.js app (:3000)
openapi.yaml           API contract shared by backend and frontend
docs/                  Requirements, design, backlog, security test plan
tests/                 Backend test suite (run by CI)
app/, alembic/         Earlier persistence implementation, kept with its tests
```

## Run locally

Prerequisites: Docker Desktop, Node.js 20+, Python 3.12 (for tests).

```bash
# 1. Backend: PostgreSQL, Redis, API on http://localhost:8000, scan worker
cp .env.example .env            # optional: GITHUB_TOKEN, OPENROUTER_API_KEY
docker compose up -d --build
curl http://localhost:8000/api/health          # {"status":"ok"}

# 2. Frontend on http://localhost:3000
cd frontend
cat > .env.local <<'EOF'
NEXT_PUBLIC_API_MODE=live
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
EOF
npm ci
npm run dev
```

API documentation: http://localhost:8000/api/docs

Stop the backend with `docker compose down` (add `-v` to delete the database).

## Checks

```bash
pip install -r requirements.txt
ruff check .                       # lint (rules pinned in ruff.toml)
pytest tests/                      # backend tests, as in CI
python test_platform_e2e.py        # live E2E against the running stack
cd frontend && npm test            # frontend tests
```
