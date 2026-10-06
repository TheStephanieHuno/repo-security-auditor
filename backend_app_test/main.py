from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_app_test.db.session import engine, Base  # <-- Updated import
from backend_app_test.db import models                  # <-- Updated import
from backend_app_test.routers import (                  # <-- Updated import
    auth,
    users,
    repositories,
    scans,
    findings,
    reports,
    dashboard,
    integrations,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-creates database tables on startup if not present
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Repo Security Auditor API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Enable CORS for Next.js / front end
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all 8 feature routers under /api
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(repositories.router, prefix="/api")
app.include_router(scans.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}