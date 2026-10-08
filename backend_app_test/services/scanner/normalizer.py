import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from backend_app_test.db.models import Finding as DBFinding

def normalize_scanner_findings(raw_findings: List[Dict[str, Any]], scan_id: uuid.UUID, repository_id: uuid.UUID) -> List[DBFinding]:
    db_findings = []
    now = datetime.now(timezone.utc)
    for item in raw_findings:
        db_finding = DBFinding(
            id=uuid.uuid4(),
            scan_id=scan_id,
            repository_id=repository_id,
            severity=item.get("severity", "medium").lower(),
            confidence=item.get("confidence", "high").lower(),
            category=item.get("category", "General Security"),
            title=item.get("title", "Security Issue"),
            description=item.get("description", ""),
            file_path=item.get("filePath", "unknown"),
            line_start=item.get("lineStart"),
            line_end=item.get("lineEnd"),
            code_snippet=item.get("codeSnippet"),
            recommendation=item.get("recommendation", "Review and remediate issue."),
            ai_explanation=item.get("aiExplanation"),
            review_status="open",
            review_note=None,
            reviewed_by=None,
            reviewed_at=None,
            created_at=now
        )
        db_findings.append(db_finding)
    return db_findings
