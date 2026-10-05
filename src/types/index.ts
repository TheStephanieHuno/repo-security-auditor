// Domain types for the Repo Security Auditor.
// These are re-exported from the canonical data.ts so all app code
// imports from @/types, not directly from data.ts.

export type {
  Severity,
  Category,
  FindingStatus,
  ScanStatus,
  DemoOutcome,
  Repository,
  Scan,
  Finding,
  RepositoryContext,
} from "@/app/data"

export type ScanOutcome = "queued" | "running" | "completed_with_findings" | "completed_clean" | "failed" | "cancelled"
export interface Branch { name: string; is_default: boolean; last_commit_sha?: string }
export interface User { name: string; email: string; role?: string; authenticated: boolean }
export interface RegisterRequest { name: string; email: string; password: string }
export interface Report { id: string; scan_id: string; status: "generating" | "ready" | "failed"; file_name: string; error_reason?: string }
export function getScanOutcome(scan: { status: string; findings?: number; findingsSnapshot?: unknown[] }): ScanOutcome {
  const status = scan.status.toLowerCase()
  if (status === "queued") return "queued"
  if (status === "running") return "running"
  if (status === "failed") return "failed"
  if (status === "cancelled") return "cancelled"
  if (status === "partial") return "completed_with_findings"
  return (scan.findings ?? scan.findingsSnapshot?.length ?? 0) > 0 ? "completed_with_findings" : "completed_clean"
}

// The API polling response shape for scan status endpoint.
export interface ScanStatusResult {
  id: string
  status: string
  stage: number
  progress: number
}

// ─── Request / Response envelope types ────────────────────────────────────────

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface LoginRequest {
  email: string
  password: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

export interface ResetRequest {
  email: string
}
export interface PasswordResetConfirm { token: string; password: string }

export interface ProfileUpdate {
  name: string
  email: string
}

export interface PasswordUpdate {
  current_password: string
  new_password: string
}

export interface RepositoryCreate {
  url: string
}

export interface RepositoryValidate {
  url: string
}

export interface ValidateResponse {
  accessible: boolean
  name?: string
  description?: string
  language?: string
  branch?: string
  visibility?: string
  commit?: string
  error?: string
}

export interface ScanTrigger {
  repo_id: string
  branch?: string
  outcome?: string // mock-only field for demo outcome
}


export interface FindingQuery {
  scan_id?: string
  repo_id?: string
  category?: string
  severity?: string
  status?: string
  scanner?: string
  search?: string
  sort?: string
  direction?: "asc" | "desc"
  page?: number
  page_size?: number
}

export interface FindingUpdate {
  status: string
  review_note?: string
}

export interface ReportCreate {
  scan_id: string
}

export interface GitHubConnect {
  token?: string
}

export interface GithubIntegration {
  connected: boolean
}

export interface UserSettings {
  completion: boolean
  failure: boolean
}

export interface DashboardMetrics {
  total_repositories: number
  total_scans: number
  total_findings: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  recent_scans: import("@/app/data").Scan[]
  top_repositories: import("@/app/data").Repository[]
}
