import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_app_test.db.session import engine, Base
from backend_app_test.db import models  # noqa: F401  (registers tables before create_all)
from backend_app_test.routers import (
    auth, users, repositories, scans, findings, reports, dashboard, integrations,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
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

# Dev origins for the Next.js frontend. Next.js silently moves to the next free
# port when 3000 is taken, so allow a small range or sign-up gets blocked by CORS
# and surfaces as "could not reach the API". Override with CORS_ORIGINS (comma-separated).
_DEFAULT_CORS_ORIGINS = ",".join(
    origin
    for port in range(3000, 3006)
    for origin in (f"http://localhost:{port}", f"http://127.0.0.1:{port}")
) + ",http://localhost:8000,http://127.0.0.1:8000"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
