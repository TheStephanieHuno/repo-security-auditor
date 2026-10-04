import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

# Import the models automatically generated from your OpenAPI design
from app.schemas.generated import (
    LoginRequest,
    AuthResponse,
    AuthData,
    User,
    ScanResponse,
    Scan,
    ScanStatus,
    FindingsCount,
    StartScanRequest,
)

app = FastAPI(
    title="Repo Security Auditor API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Allow requests from your Next.js / frontend dev server (port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health Check ──
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}

# ── Authentication ──
@app.post("/api/auth/login", response_model=AuthResponse, tags=["Authentication"])
async def login(body: LoginRequest):
    mock_user = User(
        id=uuid.uuid4(),
        name="Alex Auditor",
        email=body.email,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return AuthResponse(
        status="success",
        data=AuthData(token="sample-jwt-token-xyz123", user=mock_user),
    )

# ── Scans (P0 Requirement) ──
@app.post("/api/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED, tags=["Scans"])
async def start_scan(body: StartScanRequest):
    new_scan = Scan(
        id=uuid.uuid4(),
        repositoryId=body.repositoryId,
        branch=body.branch,
        status=ScanStatus.queued,
        progress=0,
        findingsCount=FindingsCount(critical=0, high=0, medium=0, low=0, info=0),
        startedAt=None,
        completedAt=None,
        cancelledAt=None,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return ScanResponse(status="success", data=new_scan)