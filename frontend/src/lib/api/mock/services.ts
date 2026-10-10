// Mock service implementations.
// These reproduce the demo behavior behind the service API.
// Components must NOT import this file directly — use src/lib/api/index.ts.

import {
  createDemoFindings,
  getScanFindings,
  getFindingContext,
  repositoryMetadata,
  type DemoOutcome,
  type Finding,
  type FindingStatus,
  type Repository,
  type Scan,
  type ScanStatus as ScanStatusType,
} from "@/app/data"

import {
  mockPersist_getAuth,
  mockPersist_setAuth,
  mockPersist_getProfile,
  mockPersist_setProfile,
  mockPersist_getRepositories,
  mockPersist_setRepositories,
  mockPersist_getScans,
  mockPersist_setScans,
  mockPersist_getFindings,
  mockPersist_setFindings,
  mockPersist_setFindingStatus,
  mockPersist_getGitHubConnected,
  mockPersist_setGitHubConnected,
  mockPersist_getSettings,
  mockPersist_setSettings,
  mockPersist_getScanStartTime,
  mockPersist_setScanStartTime,
  mockPersist_clearScanProgress,
  mockPersist_reset,
  MOCK_LOGIN_EMAIL,
  type MockProfile,
} from "./persist"

import type {
  Paginated,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  ResetRequest,
  ProfileUpdate,
  PasswordUpdate,
  RepositoryCreate,
  RepositoryValidate,
  ValidateResponse,
  ScanTrigger,
  ScanStatusResult,
  FindingQuery,
  FindingUpdate,
  ReportCreate,
  PasswordResetConfirm,
  DashboardMetrics,
  Branch,
  Report,
  GithubIntegration,
  GitHubConnect,
  UserSettings,
} from "@/types"

/** Simulated latency so mock feels realistic */
function delay(ms = 400): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

function paginate<T>(items: T[], page = 1, page_size = 50): Paginated<T> {
  const start = (page - 1) * page_size
  return {
    items: items.slice(start, start + page_size),
    total: items.length,
    page,
    page_size,
  }
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/auth/login
// Request: LoginRequest   Response: AuthResponse
// TODO(live): replace mock branch with apiClient.post<AuthResponse>(endpoints.auth.login, body)
export async function mockLogin(body: LoginRequest): Promise<AuthResponse> {
  await delay(750)
  if (
    body.email !== MOCK_LOGIN_EMAIL ||
    body.password !== "demo-security"
  ) {
    throw new Error(
      "Invalid email or password.",
    )
  }
  mockPersist_setAuth(true, true)
  return { access_token: "demo-token", token_type: "bearer" }
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/auth/register
// Request: RegisterRequest   Response: AuthResponse
export async function mockRegister(body: RegisterRequest): Promise<AuthResponse> {
  await delay(750)
  if (!body.name.trim() || !body.email.includes("@") || body.password.length < 8) throw new Error("Please provide valid registration details.")
  mockPersist_setProfile({ name: body.name.trim(), email: body.email.trim() })
  mockPersist_setAuth(true, true)
  return { access_token: "demo-token", token_type: "bearer" }
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/auth/logout
// Request: None   Response: None
// TODO(live): replace mock branch with apiClient.post(endpoints.auth.logout)
export async function mockLogout(): Promise<void> {
  await delay(200)
  mockPersist_setAuth(false, false)
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/users/me
// Request: None   Response: User
// TODO(live): replace mock branch with apiClient.get<User>(endpoints.users.me)
export async function mockGetSession() {
  await delay(100)
  const auth = mockPersist_getAuth()
  if (!auth) throw new Error("Unauthenticated")
  const profile = mockPersist_getProfile()
  return { ...profile, authenticated: true }
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/auth/reset
// Request: ResetRequest   Response: None
// TODO(live): replace mock branch with apiClient.post(endpoints.auth.resetPassword, body)
export async function mockRequestPasswordReset(_body: ResetRequest): Promise<void> {
  await delay(600)
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/auth/password-reset/confirm
export async function mockConfirmPasswordReset(body: PasswordResetConfirm): Promise<void> {
  await delay(500)
  if (body.token === "expired-reset-token") throw new Error("This reset link has expired.")
  if (body.token !== "valid-reset-token") throw new Error("This reset link is invalid.")
  if (body.password.length < 8) throw new Error("Use at least 8 characters.")
}

// ─── Users ────────────────────────────────────────────────────────────────────

// PLACEHOLDER: connect to FastAPI
// Endpoint: PUT /api/users/me
// Request: ProfileUpdate   Response: User
// TODO(live): replace mock branch with apiClient.put<User>(endpoints.users.me, body)
export async function mockUpdateProfile(body: ProfileUpdate): Promise<MockProfile> {
  await delay(500)
  mockPersist_setProfile(body)
  return body
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: PUT /api/users/me/password
// Request: PasswordUpdate   Response: None
// TODO(live): replace mock branch with apiClient.put(endpoints.users.password, body)
export async function mockUpdatePassword(body: PasswordUpdate): Promise<void> {
  await delay(600)
  if (!body.current_password || !body.new_password)
    throw new Error("Both current and new passwords are required.")
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/users/me (role toggle for demo)
// ─── Repositories ─────────────────────────────────────────────────────────────

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/repositories
// Request: None   Response: Paginated<Repository>
// TODO(live): replace mock branch with apiClient.get<Paginated<Repository>>(endpoints.repositories.list)
export async function mockGetRepositories(
  page = 1,
  page_size = 50,
): Promise<Paginated<Repository>> {
  await delay(300)
  const all = mockPersist_getRepositories().filter(
    (r) => r.access !== "denied",
  )
  return paginate(all, page, page_size)
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/repositories/{id}
// Request: None   Response: Repository
// TODO(live): replace mock branch with apiClient.get<Repository>(endpoints.repositories.detail(id))
export async function mockGetRepository(id: string): Promise<Repository> {
  await delay(200)
  const repo = mockPersist_getRepositories().find((r) => r.id === id)
  if (!repo) throw new Error("Repository not found")
  return repo
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/repositories/{id}/branches
// Request: None   Response: Branch[]
export async function mockGetRepositoryBranches(repoId: string): Promise<Branch[]> {
  await delay(250)
  const repo = mockPersist_getRepositories().find((item) => item.id === repoId)
  if (!repo) throw new Error("Repository not found")
  const names = repo.id === "docs" ? [repo.branch] : [repo.branch, "develop", "release/2026.10", "feature/security-hardening"]
  return names.filter((name, index) => names.indexOf(name) === index).map((name, index) => ({ name, is_default: name === repo.branch, last_commit_sha: `${repo.commit}-${index}` }))
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/repositories
// Request: RepositoryCreate   Response: Repository
// TODO(live): replace mock branch with apiClient.post<Repository>(endpoints.repositories.list, body)
export async function mockCreateRepository(
  body: RepositoryCreate,
): Promise<Repository> {
  await delay(800)
  const url = body.url.trim()
  const match = url.match(/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?$/)
  if (!match) throw new Error("Invalid GitHub repository URL")
  const [, owner, repoName] = match
  const name = `${owner}/${repoName}`
  const repos = mockPersist_getRepositories()
  const existing = repos.find(
    (r) => r.name.toLowerCase() === name.toLowerCase(),
  )
  if (existing) return existing
  const newRepo: Repository = repositoryMetadata({
    id: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    name,
    description: "",
    language: "Unknown",
    branch: "main",
    commit: "unknown",
    visibility: "Private",
    connected: new Date().toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }),
    url,
    owner,
  })
  mockPersist_setRepositories([...repos, newRepo])
  return newRepo
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/repositories/validate
// Request: RepositoryValidate   Response: ValidateResponse
// TODO(live): replace mock branch with apiClient.post<ValidateResponse>(endpoints.repositories.validate, body)
export async function mockValidateRepository(
  body: RepositoryValidate,
): Promise<ValidateResponse> {
  await delay(1200)
  const url = body.url.trim()
  const match = url.match(/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?$/)
  if (!match) return { accessible: false, error: "Not a valid GitHub URL" }
  const [, owner, repoName] = match
  return {
    accessible: true,
    name: `${owner}/${repoName}`,
    description: "Repository access confirmed",
    language: "TypeScript",
    branch: "main",
    visibility: "Private",
    commit: "abc1234",
  }
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: DELETE /api/repositories/{id}
// Request: None   Response: None
// TODO(live): replace mock branch with apiClient.delete(endpoints.repositories.detail(id))
export async function mockDeleteRepository(id: string): Promise<void> {
  await delay(400)
  const repos = mockPersist_getRepositories().filter((r) => r.id !== id)
  mockPersist_setRepositories(repos)
}

export async function mockSetRepositoryAccess(
  repoId: string,
  granted: boolean,
): Promise<void> {
  await delay(200)
  const repos = mockPersist_getRepositories().map((r) =>
    r.id === repoId ? { ...r, access: granted ? ("granted" as const) : ("denied" as const) } : r,
  )
  mockPersist_setRepositories(repos)
}

// ─── Scans ────────────────────────────────────────────────────────────────────

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/scans
// Request: None   Response: Paginated<Scan>
// TODO(live): replace mock branch with apiClient.get<Paginated<Scan>>(endpoints.scans.list)
export async function mockGetScans(
  page = 1,
  page_size = 50,
  repoId?: string,
): Promise<Paginated<Scan>> {
  await delay(300)
  const visibleIds = new Set(
    mockPersist_getRepositories()
      .filter((r) => r.access !== "denied")
      .map((r) => r.id),
  )
  let all = mockPersist_getScans().filter((s) => visibleIds.has(s.repoId))
  if (repoId) all = all.filter((s) => s.repoId === repoId)
  return paginate(all, page, page_size)
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/scans/{id}
// Request: None   Response: Scan
// TODO(live): replace mock branch with apiClient.get<Scan>(endpoints.scans.detail(id))
export async function mockGetScan(id: string): Promise<Scan> {
  await delay(200)
  const scan = mockPersist_getScans().find((s) => s.id === id)
  if (!scan) throw new Error("Scan not found")
  return scan
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/scans
// Request: ScanTrigger   Response: Scan
// TODO(live): replace mock branch with apiClient.post<Scan>(endpoints.scans.trigger, body)
export async function mockTriggerScan(body: ScanTrigger): Promise<Scan> {
  await delay(500)
  const repos = mockPersist_getRepositories()
  const repo = repos.find((r) => r.id === body.repo_id)
  if (!repo) throw new Error("Repository not found")
  if (repo.access === "denied")
    throw new Error("You do not have permission to scan this repository.")
  if (!mockPersist_getGitHubConnected())
    throw new Error("Restore the demo GitHub connection before starting a scan.")

  const scans = mockPersist_getScans()
  const findings = mockPersist_getFindings()
  const outcome: DemoOutcome = (body.outcome as DemoOutcome) ?? "Completed"
  const id = String(Math.max(12, ...scans.map((s) => Number(s.id))) + 1)
  const started = new Date()

  const candidates =
    outcome === "No findings" ? [] : createDemoFindings(repo, findings, id)
  const captured = candidates

  const job: Scan = {
    id,
    repoId: body.repo_id,
    status: "Queued",
    date: `${started.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })} · ${started.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" })}`,
    relative: "Just now",
    duration: "—",
    progress: 0,
    stage: 0,
    isNew: true,
    commit: repo.commit,
    branch: body.branch || repo.branch,
    outcome,
    findingsSnapshot: structuredClone(
      captured.map((f) => ({ ...f, context: getFindingContext(f) })),
    ),
    findingIds: captured.map((f) => f.id),
    startedAt: started.toISOString(),
  }

  // Record start time for progress calculation
  mockPersist_setScanStartTime(id, started.getTime())
  mockPersist_setScans([job, ...scans])
  return job
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/scans/{id}/status
// Request: None   Response: ScanStatus
// TODO(live): replace mock branch with apiClient.get<ScanStatus>(endpoints.scans.status(id))
export async function mockGetScanStatus(id: string): Promise<ScanStatusResult> {
  await delay(100)
  const scans = mockPersist_getScans()
  const scan = scans.find((s) => s.id === id)
  if (!scan) throw new Error("Scan not found")

  // If already terminal, return immediately
  if (["Completed", "Failed", "Partial", "Cancelled"].includes(scan.status)) {
    return { id, status: scan.status, stage: scan.stage, progress: scan.progress }
  }

  // Calculate progress from wall-clock time
  const startTime = mockPersist_getScanStartTime(id)
  if (!startTime) {
    return { id, status: scan.status, stage: scan.stage, progress: scan.progress }
  }

  const elapsed = Date.now() - startTime
  // Each stage takes ~2 seconds (matches old 2000ms interval)
  const stage = Math.min(Math.floor(elapsed / 2000) + 1, 10)
  const progress = stage * 10

  let newStatus: ScanStatusType = stage > 0 ? "Running" : "Queued"

  if (stage >= 10) {
    if (scan.outcome === "Failed") {
      // Advance the scan to failed state
      const updatedScans = scans.map((s) =>
        s.id === id
          ? {
              ...s,
              status: "Failed" as ScanStatusType,
              stage: 1,
              progress: 10,
              duration: "4s (demo)",
              relative: "Just now",
              completedAt: new Date().toISOString(),
            }
          : s,
      )
      mockPersist_setScans(updatedScans)
      mockPersist_clearScanProgress(id)
      return { id, status: "Failed", stage: 1, progress: 10 }
    }

    newStatus = scan.outcome === "Partial" ? "Partial" : "Completed"

    // Write findings on completion
    if (scan.findingsSnapshot?.length) {
      const currentFindings = mockPersist_getFindings()
      const known = new Set(currentFindings.map((f) => f.id))
      const toAdd = scan.findingsSnapshot.filter((f) => !known.has(f.id))
      if (toAdd.length) {
        mockPersist_setFindings([...currentFindings, ...toAdd])
      }
    }

    const updatedScans = scans.map((s) =>
      s.id === id
        ? {
            ...s,
            status: newStatus,
            stage: 10,
            progress: 100,
            duration: "20s (demo)",
            relative: "Just now",
            completedAt: new Date().toISOString(),
          }
        : s,
    )
    mockPersist_setScans(updatedScans)
    mockPersist_clearScanProgress(id)
    return { id, status: newStatus, stage: 10, progress: 100 }
  }

  // Update in-progress state in storage
  const updatedScans = scans.map((s) =>
    s.id === id ? { ...s, status: newStatus, stage, progress } : s,
  )
  mockPersist_setScans(updatedScans)

  return { id, status: newStatus, stage, progress }
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/scans/{id}/cancel
// Request: None   Response: Scan
// TODO(live): replace mock branch with apiClient.post<Scan>(endpoints.scans.cancel(id))
export async function mockCancelScan(id: string): Promise<Scan> {
  await delay(300)
  const scans = mockPersist_getScans()
  const updated = scans.map((s) =>
    s.id === id && ["Running", "Queued"].includes(s.status)
      ? { ...s, status: "Cancelled" as ScanStatusType, duration: "Cancelled", findingsSnapshot: [], findingIds: [] }
      : s,
  )
  mockPersist_setScans(updated)
  mockPersist_clearScanProgress(id)
  const scan = updated.find((s) => s.id === id)
  if (!scan) throw new Error("Scan not found")
  return scan
}

// PLACEHOLDER: connect to FastAPI  
// Endpoint: GET /api/scans/{id}/findings
// Request: FindingQuery   Response: Paginated<Finding>
// TODO(live): replace mock branch with apiClient.get<Paginated<Finding>>(endpoints.scans.findings(id), ...)
export async function mockGetScanFindings(
  scanId: string,
  query: FindingQuery = {},
): Promise<Paginated<Finding>> {
  await delay(300)
  const scan = mockPersist_getScans().find((s) => s.id === scanId)
  if (!scan) throw new Error("Scan not found")
  let items = getScanFindings(scan, mockPersist_getFindings())
  if (query.category) items = items.filter((f) => f.category === query.category)
  if (query.severity) items = items.filter((f) => f.severity === query.severity)
  if (query.status) items = items.filter((f) => f.status === query.status)
  if (query.scanner) items = items.filter((f) => f.scanner === query.scanner)
  if (query.search) {
    const q = query.search.toLowerCase()
    items = items.filter(
      (f) =>
        f.title.toLowerCase().includes(q) ||
        f.file.toLowerCase().includes(q) ||
        f.rule.toLowerCase().includes(q),
    )
  }
  return paginate(items, query.page, query.page_size)
}

// ─── Findings ─────────────────────────────────────────────────────────────────

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/findings
// Request: FindingQuery   Response: Paginated<Finding>
// TODO(live): replace mock branch with apiClient.get<Paginated<Finding>>(endpoints.findings.list, { params: query })
export async function mockGetFindings(
  query: FindingQuery = {},
): Promise<Paginated<Finding>> {
  await delay(300)
  const visibleIds = new Set(
    mockPersist_getRepositories()
      .filter((r) => r.access !== "denied")
      .map((r) => r.id),
  )
  let items = mockPersist_getFindings().filter((f) => visibleIds.has(f.repoId))
  if (query.repo_id) items = items.filter((f) => f.repoId === query.repo_id)
  if (query.scan_id) items = items.filter((f) => f.scanId === query.scan_id)
  if (query.category) items = items.filter((f) => f.category === query.category)
  if (query.severity) items = items.filter((f) => f.severity === query.severity)
  if (query.status) items = items.filter((f) => f.status === query.status)
  if (query.scanner) items = items.filter((f) => f.scanner === query.scanner)
  if (query.search) {
    const q = query.search.toLowerCase()
    items = items.filter(
      (f) =>
        f.title.toLowerCase().includes(q) ||
        f.file.toLowerCase().includes(q) ||
        f.rule.toLowerCase().includes(q),
    )
  }
  return paginate(items, query.page, query.page_size)
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/findings/{id}
// Request: None   Response: Finding
// TODO(live): replace mock branch with apiClient.get<Finding>(endpoints.findings.detail(id))
export async function mockGetFinding(id: string): Promise<Finding> {
  await delay(200)
  const finding = mockPersist_getFindings().find((f) => f.id === id)
  if (!finding) throw new Error("Finding not found")
  return finding
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: PATCH /api/findings/{id}
// Request: FindingUpdate   Response: Finding
// TODO(live): replace mock branch with apiClient.patch<Finding>(endpoints.findings.detail(id), body)
export async function mockUpdateFinding(
  id: string,
  body: FindingUpdate,
): Promise<Finding> {
  await delay(400)
  const updated = mockPersist_setFindingStatus(
    id,
    body.status as FindingStatus,
    body.review_note,
  )
  if (!updated) throw new Error("Finding not found")
  return updated
}

// ─── Reports ──────────────────────────────────────────────────────────────────

const reportState = new Map<string, Report & { readyAt?: number }>()

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/reports
// Request: None   Response: Paginated<Scan>
// TODO(live): replace mock branch with apiClient.get<Paginated<Report>>(endpoints.reports.list)
export async function mockGetReports(page = 1, page_size = 50): Promise<Paginated<Scan>> {
  await delay(300)
  const completed = mockPersist_getScans().filter((s) =>
    ["Completed", "Partial"].includes(s.status),
  )
  return paginate(completed, page, page_size)
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/reports/{id}
// Request: None   Response: Report
// TODO(live): replace mock branch with apiClient.get<Report>(endpoints.reports.detail(id))
export async function mockGetReport(id: string): Promise<Report> {
  await delay(200)
  const scan = mockPersist_getScans().find(
    (s) => s.id === id && ["Completed", "Partial"].includes(s.status),
  )
  if (!scan) throw new Error("Report not found")
  const repo = mockPersist_getRepositories().find((item) => item.id === scan.repoId)
  const file_name = `${(repo?.name || "repository").replace("/", "-")}-${scan.branch || repo?.branch || "main"}-security-report-${new Date().toISOString().slice(0, 10)}.pdf`
  const existing = reportState.get(id)
  if (existing?.status === "generating" && existing.readyAt && Date.now() >= existing.readyAt) {
    const ready = { ...existing, status: "ready" as const }
    delete ready.readyAt
    reportState.set(id, ready)
    return ready
  }
  return existing || { id, scan_id: id, status: "ready", file_name }
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/reports
// Request: ReportCreate   Response: Report
// TODO(live): replace mock branch with apiClient.post<Report>(endpoints.reports.generate, body)
export async function mockGenerateReport(body: ReportCreate): Promise<Report> {
  await delay(800)
  const scan = mockPersist_getScans().find((item) => item.id === body.scan_id)
  if (!scan) throw new Error("Report not found")
  const repo = mockPersist_getRepositories().find((item) => item.id === scan.repoId)
  const file_name = `${(repo?.name || "repository").replace("/", "-")}-${scan.branch || repo?.branch || "main"}-security-report-${new Date().toISOString().slice(0, 10)}.pdf`
  const existing = reportState.get(body.scan_id)
  if (existing && ["generating", "ready"].includes(existing.status)) return existing
  if (scan.status === "Failed") {
    const failed = { id: body.scan_id, scan_id: body.scan_id, status: "failed" as const, file_name, error_reason: "The scan did not produce a complete result." }
    reportState.set(body.scan_id, failed)
    return failed
  }
  const generating = { id: body.scan_id, scan_id: body.scan_id, status: "generating" as const, file_name, readyAt: Date.now() + 1200 }
  reportState.set(body.scan_id, generating)
  return generating
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/reports/{id}/pdf
// Request: None   Response: Blob (PDF)
// TODO(live): replace mock branch with apiClient.getBlob(endpoints.reports.pdf(id))
export async function mockDownloadReportPdf(_id: string): Promise<Blob> {
  await delay(300)
  if (typeof window !== "undefined") {
    const response = await fetch("/mock/sample-report.pdf")
    if (response.ok) return response.blob()
  }
  return new Blob(["%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"], { type: "application/pdf" })
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/dashboard/metrics
// Request: None   Response: DashboardMetrics
// TODO(live): replace mock branch with apiClient.get<DashboardMetrics>(endpoints.dashboard.metrics)
export async function mockGetDashboard(): Promise<DashboardMetrics> {
  await delay(300)
  const findings = mockPersist_getFindings()
  const scans = mockPersist_getScans()
  const repos = mockPersist_getRepositories().filter((r) => r.access !== "denied")
  return {
    total_repositories: repos.length,
    total_scans: scans.length,
    total_findings: findings.length,
    critical_count: findings.filter((f) => f.severity === "Critical").length,
    high_count: findings.filter((f) => f.severity === "High").length,
    medium_count: findings.filter((f) => f.severity === "Medium").length,
    low_count: findings.filter((f) => f.severity === "Low").length,
    recent_scans: scans.slice(0, 5),
    top_repositories: repos.slice(0, 5),
  }
}

// ─── GitHub Integration ───────────────────────────────────────────────────────

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/integrations/github
// Request: None   Response: GithubIntegration
export async function mockGetGithubIntegration(): Promise<GithubIntegration> {
  await delay(200)
  return { connected: mockPersist_getGitHubConnected() }
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: POST /api/integrations/github
// Request: GitHubConnect   Response: GithubIntegration
export async function mockConnectGithub(_body: GitHubConnect): Promise<GithubIntegration> {
  await delay(500)
  mockPersist_setGitHubConnected(true)
  return { connected: true }
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: DELETE /api/integrations/github
// Request: None   Response: GithubIntegration
export async function mockDisconnectGithub(): Promise<GithubIntegration> {
  await delay(300)
  mockPersist_setGitHubConnected(false)
  return { connected: false }
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: GET /api/users/me/settings
// Request: None   Response: UserSettings
export async function mockGetSettings(): Promise<UserSettings> {
  await delay(200)
  return mockPersist_getSettings()
}

// PLACEHOLDER: connect to FastAPI
// Endpoint: PUT /api/users/me/settings
// Request: UserSettings   Response: UserSettings
export async function mockUpdateSettings(body: UserSettings): Promise<UserSettings> {
  await delay(300)
  const settings = { completion: Boolean(body.completion), failure: Boolean(body.failure) }
  mockPersist_setSettings(settings)
  return settings
}

// ─── Misc ─────────────────────────────────────────────────────────────────────

export async function mockReset(): Promise<void> {
  await delay(200)
  mockPersist_reset()
}

export { MOCK_LOGIN_EMAIL }
