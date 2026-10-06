from fastapi import APIRouter
from sqlalchemy import case, func, select

from app.api.serializers import findings_to_api, scans_to_api
from app.core.dependencies import CurrentUser, DBSession
from app.db.models import Repository, ScanStatus
from app.db.queries import owned_findings, owned_scans
from app.schemas.generated import DashboardMetrics, DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
RECENT_ITEMS = 5


@router.get("/metrics", response_model=DashboardResponse)
async def get_dashboard_metrics(user: CurrentUser, db: DBSession):
    repositories = await db.scalar(
        select(func.count(Repository.id)).where(Repository.owner_id == user.id)
    )

    scans = owned_scans(user.id).subquery()
    scan_counts = (
        await db.execute(
            select(
                func.count(),
                *(
                    func.sum(case((scans.c.status.in_(values), 1), else_=0))
                    for values in (
                        [ScanStatus.QUEUED.value],
                        [ScanStatus.RUNNING.value],
                        [ScanStatus.COMPLETED.value, ScanStatus.PARTIAL.value],
                        [ScanStatus.FAILED.value],
                        [ScanStatus.CANCELLED.value],
                    )
                ),
            ).select_from(scans)
        )
    ).one()

    findings = owned_findings(user.id).subquery()
    finding_counts = (
        await db.execute(
            select(
                func.count(),
                func.sum(case((findings.c.review_status == "OPEN", 1), else_=0)),
                *(
                    func.sum(case((findings.c.severity == severity, 1), else_=0))
                    for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
                ),
            ).select_from(findings)
        )
    ).one()
    total_scans, queued, running, completed, failed, cancelled = (value or 0 for value in scan_counts)
    total_findings, open_findings, critical, high, medium, low = (value or 0 for value in finding_counts)

    recent_scans = list((await db.execute(owned_scans(user.id).limit(RECENT_ITEMS))).scalars())
    recent_findings = list(
        (await db.execute(owned_findings(user.id).limit(RECENT_ITEMS))).scalars()
    )
    metrics = DashboardMetrics(
        repositories={"total": repositories or 0},
        scans={
            "total": total_scans,
            "queued": queued,
            "running": running,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
        },
        findings={
            "total": total_findings,
            "open": open_findings,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "info": 0,
        },
        recentScans=await scans_to_api(db, recent_scans),
        recentFindings=await findings_to_api(db, recent_findings),
    )
    return DashboardResponse(status="success", data=metrics)
