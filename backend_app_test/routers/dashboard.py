from fastapi import APIRouter
from backend_app_test.schemas.generated import (
    DashboardResponse,
    DashboardMetrics,
    FindingsCount,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics", response_model=DashboardResponse)
async def get_dashboard_metrics():
    metrics = DashboardMetrics(
        repositories={"total": 5},
        scans={"total": 24, "queued": 1, "running": 1, "completed": 20, "failed": 1, "cancelled": 1},
        findings={"total": 42, "open": 18, "critical": 2, "high": 8, "medium": 14, "low": 18, "info": 0},
        recentScans=[],
        recentFindings=[],
    )
    return DashboardResponse(status="success", data=metrics)