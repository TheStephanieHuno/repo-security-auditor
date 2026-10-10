from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend_app_test.db.session import get_db
from backend_app_test.core.dependencies import get_current_user
from backend_app_test.db.models import Repository as DBRepository, Scan as DBScan, Finding as DBFinding, User as DBUser
from backend_app_test.schemas.generated import DashboardResponse, DashboardMetrics

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics", response_model=DashboardResponse)
async def get_dashboard_metrics(current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo_count = (await db.execute(select(func.count()).select_from(DBRepository).where(DBRepository.added_by == current_user.id))).scalar() or 0
    scans_query = select(DBScan.status, func.count()).join(DBRepository, DBScan.repository_id == DBRepository.id).where(DBRepository.added_by == current_user.id).group_by(DBScan.status)
    scan_counts = {r[0]: r[1] for r in (await db.execute(scans_query)).all()}

    findings_query = select(DBFinding.severity, func.count()).join(DBRepository, DBFinding.repository_id == DBRepository.id).where(DBRepository.added_by == current_user.id).group_by(DBFinding.severity)
    finding_counts = {r[0]: r[1] for r in (await db.execute(findings_query)).all()}
    open_count = (await db.execute(select(func.count()).select_from(DBFinding).join(DBRepository, DBFinding.repository_id == DBRepository.id).where(DBRepository.added_by == current_user.id, DBFinding.review_status == "open"))).scalar() or 0

    metrics = DashboardMetrics(
        repositories={"total": repo_count},
        scans={"total": sum(scan_counts.values()), "queued": scan_counts.get("queued", 0), "running": scan_counts.get("running", 0), "completed": scan_counts.get("completed", 0), "failed": scan_counts.get("failed", 0), "cancelled": scan_counts.get("cancelled", 0)},
        findings={"total": sum(finding_counts.values()), "open": open_count, "critical": finding_counts.get("critical", 0), "high": finding_counts.get("high", 0), "medium": finding_counts.get("medium", 0), "low": finding_counts.get("low", 0), "info": finding_counts.get("info", 0)},
        recentScans=[],
        recentFindings=[]
    )
    return DashboardResponse(status="success", data=metrics)
