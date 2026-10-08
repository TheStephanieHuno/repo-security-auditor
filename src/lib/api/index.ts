// API index — the ONLY import point for the service layer.
// Switches between mock and live implementations based on NEXT_PUBLIC_API_MODE.
// Components must import ONLY from this file, never from mock/ directly.

import * as mock from "./mock/services"
import type {
  Paginated,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  ResetRequest,
  PasswordResetConfirm,
  ProfileUpdate,
  PasswordUpdate,
  RepositoryCreate,
  RepositoryValidate,
  ValidateResponse,
  ScanTrigger,
  FindingQuery,
  FindingUpdate,
  ReportCreate,
  DashboardMetrics,
  Branch,
  Report,
  GithubIntegration,
  GitHubConnect,
  UserSettings,
  User,
} from "@/types"
import type {
  Category,
  Finding,
  FindingStatus,
  Repository,
  Scan,
  ScanStatus,
  Severity,
} from "@/app/data"
import { apiClient, setAuthToken } from "./client"
import { endpoints } from "./endpoints"

const isLive = process.env.NEXT_PUBLIC_API_MODE === "live"

interface ApiRepository {
  id: string
  name: string
  owner?: string
  url?: string
  defaultBranch?: string
  createdAt?: string
}

interface ApiBranch {
  name: string
  isDefault: boolean
  lastCommit?: string
}

interface ApiScan {
  id: string
  repositoryId: string
  status: string
  createdAt?: string
  startedAt?: string
  completedAt?: string
  progress?: number
  branch?: string
}

interface ApiFinding {
  id: string
  repositoryId: string
  scanId?: string
  title: string
  severity: string
  category?: string
  confidence?: string
  filePath?: string
  lineStart?: number
  description?: string
  codeSnippet?: string
  recommendation?: string
  reviewStatus?: string
  reviewNote?: string
  aiExplanation?: string
}

interface ApiValidateResult {
  valid?: boolean
  name?: string
  message?: string
  defaultBranch?: string
}

interface ApiReport {
  id: string
  scanId?: string
  status: string
  fileUrl?: string
}

interface ApiSettings {
  onScanCompletion: boolean
  onScanFailure: boolean
}

interface ApiDashboard {
  repositories?: { total?: number }
  scans?: { total?: number }
  findings?: {
    total?: number
    critical?: number
    high?: number
    medium?: number
    low?: number
  }
  recentScans?: ApiScan[]
}

export function toTitleCase(str?: string) {
  if (!str) return ""
  if (str === "false_positive") return "False positive"
  if (str === "acknowledged") return "Reviewed"
  if (str === "False positive") return "false_positive"
  if (str === "Reviewed") return "acknowledged"
  if (str === "Open") return "open"
  if (str === "Resolved") return "resolved"
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

function computeRelative(dateStr?: string) {
  if (!dateStr) return "—"
  const ms = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(ms / 60000)
  if (minutes < 1) return "Just now"
  if (minutes < 60) return `${minutes} minute${minutes > 1 ? "s" : ""} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`
  const days = Math.floor(hours / 24)
  return `${days} day${days > 1 ? "s" : ""} ago`
}

function mapRepo(r: ApiRepository): Repository {
  return {
    id: r.id,
    name: r.name,
    description: "",
    language: "—",
    branch: r.defaultBranch || "—",
    commit: "—",
    visibility: "—",
    connected: r.createdAt ? new Date(r.createdAt).toLocaleDateString() : "",
    owner: r.owner,
    url: r.url,
  }
}

function mapScan(s: ApiScan): Scan {
  return {
    id: s.id,
    repoId: s.repositoryId,
    status: toTitleCase(s.status) as ScanStatus,
    date: s.createdAt ? new Date(s.createdAt).toLocaleDateString() : "",
    relative: computeRelative(s.startedAt),
    duration: "—",
    progress: s.progress ?? 0,
    stage: s.progress ? Math.floor(s.progress / 10) : 0,
    branch: s.branch,
    startedAt: s.startedAt,
    completedAt: s.completedAt
  }
}

function mapFinding(f: ApiFinding): Finding & { aiExplanation?: string } {
  return {
    id: f.id,
    repoId: f.repositoryId,
    scanId: f.scanId,
    title: f.title,
    severity: toTitleCase(f.severity) as Severity,
    category: (f.category || "Code") as Category,
    confidence: (toTitleCase(f.confidence) || "Medium") as Finding["confidence"],
    file: f.filePath || "—",
    line: f.lineStart || 1,
    scanner: "—",
    rule: f.title,
    description: f.description || "",
    evidence: f.codeSnippet || "",
    fixed: "",
    remediation: f.recommendation || "",
    impact: "",
    status: (toTitleCase(f.reviewStatus) || "Open") as FindingStatus,
    reviewNote: f.reviewNote,
    aiExplanation: f.aiExplanation || "",
    aiState: f.aiExplanation ? undefined : "unavailable"
  }
}

function mapReport(r: ApiReport): Report {
  return {
    id: r.id,
    scan_id: r.scanId ?? "",
    status: r.status as Report["status"],
    file_name: r.fileUrl || "report.pdf",
  }
}

export const api = {
  // ─── Auth ──────────────────────────────────────────────────────────────────
  login: async (body: LoginRequest): Promise<AuthResponse> => {
    if (isLive) {
      const res = await apiClient.post<{ token: string; user: unknown }>(endpoints.auth.login, body)
      setAuthToken(res.token)
      return { access_token: res.token, token_type: "bearer" }
    }
    return mock.mockLogin(body)
  },

  register: async (body: RegisterRequest): Promise<AuthResponse> => {
    if (isLive) {
      const res = await apiClient.post<{ token: string; user: unknown }>(endpoints.auth.register, body)
      setAuthToken(res.token)
      return { access_token: res.token, token_type: "bearer" }
    }
    return mock.mockRegister(body)
  },

  logout: async (): Promise<void> => {
    if (isLive) {
      try {
        await apiClient.post(endpoints.auth.logout)
      } finally {
        setAuthToken(null)
      }
      return
    }
    return mock.mockLogout()
  },

  getSession: (): Promise<User> => {
    if (isLive) {
      return apiClient.get<Omit<User, "authenticated">>(endpoints.users.me).then(user => ({ ...user, authenticated: true }))
    }
    return mock.mockGetSession()
  },

  requestPasswordReset: (body: ResetRequest): Promise<void> => {
    if (isLive) {
      return apiClient.post(endpoints.auth.passwordResetRequest, body)
    }
    return mock.mockRequestPasswordReset(body)
  },

  confirmPasswordReset: (body: PasswordResetConfirm): Promise<void> => {
    if (isLive) {
      return apiClient.post(endpoints.auth.passwordResetConfirm, { token: body.token, newPassword: body.password })
    }
    return mock.mockConfirmPasswordReset(body)
  },

  // ─── Users ─────────────────────────────────────────────────────────────────
  updateProfile: (body: ProfileUpdate) => {
    if (isLive) {
      return apiClient.put<unknown>(endpoints.users.me, body)
    }
    return mock.mockUpdateProfile(body)
  },

  updatePassword: (body: PasswordUpdate): Promise<void> => {
    if (isLive) {
      return apiClient.put(endpoints.users.password, {
        currentPassword: body.current_password,
        newPassword: body.new_password
      })
    }
    return mock.mockUpdatePassword(body)
  },


  // ─── Repositories ──────────────────────────────────────────────────────────
  getRepositories: (page = 1, page_size = 50): Promise<Paginated<Repository>> => {
    if (isLive) {
      return apiClient.get<Paginated<ApiRepository>>(`${endpoints.repositories.list}?page=${page}&pageSize=${page_size}`)
        .then(res => ({ ...res, items: res.items.map(mapRepo) }))
    }
    return mock.mockGetRepositories(page, page_size)
  },

  getRepository: (id: string): Promise<Repository> => {
    if (isLive) {
      return apiClient.get<ApiRepository>(endpoints.repositories.detail(id)).then(mapRepo)
    }
    return mock.mockGetRepository(id)
  },

  getRepositoryBranches: (id: string): Promise<Branch[]> => {
    if (isLive) {
      return apiClient.get<ApiBranch[]>(endpoints.repositories.branches(id)).then(branches => 
        branches.map(b => ({ name: b.name, is_default: b.isDefault, last_commit_sha: b.lastCommit }))
      )
    }
    return mock.mockGetRepositoryBranches(id)
  },

  createRepository: (body: RepositoryCreate): Promise<Repository> => {
    if (isLive) {
      return apiClient.post<ApiRepository>(endpoints.repositories.list, body).then(mapRepo)
    }
    return mock.mockCreateRepository(body)
  },

  validateRepository: (body: RepositoryValidate): Promise<ValidateResponse> => {
    if (isLive) {
      return apiClient.post<ApiValidateResult>(endpoints.repositories.validate, body).then(res => ({
        accessible: res.valid ?? false,
        name: res.name,
        description: "",
        language: "",
        branch: res.defaultBranch,
        visibility: "",
        commit: "",
        error: res.message,
      }))
    }
    return mock.mockValidateRepository(body)
  },

  deleteRepository: (id: string): Promise<void> => {
    if (isLive) {
      return apiClient.delete(endpoints.repositories.detail(id))
    }
    return mock.mockDeleteRepository(id)
  },


  // ─── Scans ─────────────────────────────────────────────────────────────────
  getScans: (page = 1, page_size = 50, repoId?: string): Promise<Paginated<Scan>> => {
    if (isLive) {
      const qs = new URLSearchParams()
      qs.set("page", page.toString())
      qs.set("pageSize", page_size.toString())
      if (repoId) qs.set("repositoryId", repoId)
      return apiClient.get<Paginated<ApiScan>>(`${endpoints.scans.list}?${qs.toString()}`)
        .then(res => ({ ...res, items: res.items.map(mapScan) }))
    }
    return mock.mockGetScans(page, page_size, repoId)
  },

  getScan: (id: string): Promise<Scan> => {
    if (isLive) {
      return apiClient.get<ApiScan>(endpoints.scans.detail(id)).then(mapScan)
    }
    return mock.mockGetScan(id)
  },

  triggerScan: (body: ScanTrigger): Promise<Scan> => {
    if (isLive) {
      return apiClient.post<ApiScan>(endpoints.scans.trigger, {
        repositoryId: body.repo_id,
        branch: body.branch,
      }).then(mapScan)
    }
    return mock.mockTriggerScan(body)
  },

  getScanStatus: (id: string) => {
    if (isLive) {
      // Backend status is lowercase: queued | running | completed | failed | cancelled
      // Frontend ScanStatusResult expects id, status, stage, progress
      return apiClient.get<{ id: string; status: string; progress?: number }>(endpoints.scans.status(id)).then(res => ({
        id: res.id,
        status: res.status,
        progress: res.progress ?? 0,
        stage: Math.floor((res.progress ?? 0) / 10),
      }))
    }
    return mock.mockGetScanStatus(id)
  },

  cancelScan: (id: string): Promise<Scan> => {
    if (isLive) {
      return apiClient.post<ApiScan>(endpoints.scans.cancel(id)).then(mapScan)
    }
    return mock.mockCancelScan(id)
  },

  getScanFindings: (scanId: string, query: FindingQuery = {}): Promise<Paginated<Finding>> => {
    if (isLive) {
      const qs = new URLSearchParams()
      if (query.page) qs.append("page", query.page.toString())
      if (query.page_size) qs.append("pageSize", query.page_size.toString())
      if (query.severity) qs.append("severity", query.severity)
      return apiClient.get<Paginated<ApiFinding>>(`${endpoints.scans.findings(scanId)}?${qs.toString()}`)
        .then(res => ({ ...res, items: res.items.map(mapFinding) }))
    }
    return mock.mockGetScanFindings(scanId, query)
  },

  // ─── Findings ──────────────────────────────────────────────────────────────
  getFindings: (query: FindingQuery = {}): Promise<Paginated<Finding>> => {
    if (isLive) {
      const qs = new URLSearchParams()
      if (query.page) qs.append("page", query.page.toString())
      if (query.page_size) qs.append("pageSize", query.page_size.toString())
      if (query.scan_id) qs.append("scanId", query.scan_id)
      if (query.repo_id) qs.append("repositoryId", query.repo_id)
      if (query.severity) qs.append("severity", query.severity)
      return apiClient.get<Paginated<ApiFinding>>(`${endpoints.findings.list}?${qs.toString()}`)
        .then(res => ({ ...res, items: res.items.map(mapFinding) }))
    }
    return mock.mockGetFindings(query)
  },

  getFinding: (id: string): Promise<Finding> => {
    if (isLive) {
      return apiClient.get<ApiFinding>(endpoints.findings.detail(id)).then(mapFinding)
    }
    return mock.mockGetFinding(id)
  },

  updateFinding: (id: string, body: FindingUpdate): Promise<Finding> => {
    if (isLive) {
      // Map UI reviewStatus to backend enum
      let reviewStatus = "open"
      if (body.status === "False positive") reviewStatus = "false_positive"
      else if (body.status === "Reviewed") reviewStatus = "acknowledged"
      else if (body.status === "Resolved") reviewStatus = "resolved"

      return apiClient.patch<ApiFinding>(endpoints.findings.detail(id), {
        reviewStatus,
        reviewNote: body.review_note
      }).then(mapFinding)
    }
    return mock.mockUpdateFinding(id, body)
  },

  // ─── Reports ───────────────────────────────────────────────────────────────
  getReports: (page = 1, page_size = 50, scanId?: string): Promise<Paginated<Report>> => {
    if (isLive) {
      const q = new URLSearchParams()
      q.set("page", page.toString())
      q.set("pageSize", page_size.toString())
      if (scanId) q.set("scanId", scanId)
      return apiClient.get<Paginated<ApiReport>>(`${endpoints.reports.list}?${q.toString()}`)
        .then(res => ({ ...res, items: res.items.map(mapReport) }))
    }
    return mock.mockGetReports(page, page_size) as unknown as Promise<Paginated<Report>>
  },

  getReport: (id: string): Promise<Report> => {
    if (isLive) {
      return apiClient.get<ApiReport>(endpoints.reports.detail(id))
        .then(mapReport)
    }
    return mock.mockGetReport(id)
  },

  generateReport: (body: ReportCreate): Promise<Report> => {
    if (isLive) {
      return apiClient.post<ApiReport>(endpoints.reports.generate, { scanId: body.scan_id })
        .then(mapReport)
    }
    return mock.mockGenerateReport(body)
  },

  downloadReportPdf: (id: string): Promise<Blob> => {
    if (isLive) {
      return apiClient.getBlob(endpoints.reports.pdf(id))
    }
    return mock.mockDownloadReportPdf(id)
  },

  // ─── Dashboard ─────────────────────────────────────────────────────────────
  getDashboard: (): Promise<DashboardMetrics> => {
    if (isLive) {
      return apiClient.get<ApiDashboard>(endpoints.dashboard.metrics).then(metrics => ({
        total_repositories: metrics.repositories?.total || 0,
        total_scans: metrics.scans?.total || 0,
        total_findings: metrics.findings?.total || 0,
        critical_count: metrics.findings?.critical || 0,
        high_count: metrics.findings?.high || 0,
        medium_count: metrics.findings?.medium || 0,
        low_count: metrics.findings?.low || 0,
        recent_scans: (metrics.recentScans || []).map(mapScan),
        top_repositories: [], // We'll ignore top_repositories since the backend doesn't provide it
      }))
    }
    return mock.mockGetDashboard()
  },

  // ─── GitHub Integration ────────────────────────────────────────────────────
  getGithubIntegration: (): Promise<GithubIntegration> => {
    if (isLive) {
      return apiClient.get<GithubIntegration>(endpoints.integrations.github)
    }
    return mock.mockGetGithubIntegration()
  },

  connectGithub: (body: GitHubConnect = {}): Promise<GithubIntegration> => {
    if (isLive) {
      return apiClient.post<GithubIntegration>(endpoints.integrations.github, body)
    }
    return mock.mockConnectGithub(body)
  },

  disconnectGithub: (): Promise<GithubIntegration> => {
    if (isLive) {
      return apiClient.delete<GithubIntegration>(endpoints.integrations.github)
    }
    return mock.mockDisconnectGithub()
  },

  getSettings: (): Promise<UserSettings> => {
    if (isLive) {
      return apiClient.get<ApiSettings>(endpoints.users.settings).then(res => ({
        completion: res.onScanCompletion,
        failure: res.onScanFailure
      }))
    }
    return mock.mockGetSettings()
  },

  updateSettings: (body: UserSettings): Promise<UserSettings> => {
    if (isLive) {
      return apiClient.put<ApiSettings>(endpoints.users.settings, {
        onScanCompletion: body.completion,
        onScanFailure: body.failure
      }).then(res => ({
        completion: res.onScanCompletion,
        failure: res.onScanFailure
      }))
    }
    return mock.mockUpdateSettings(body)
  },

  // ─── Misc ──────────────────────────────────────────────────────────────────
  reset: (): Promise<void> => mock.mockReset(),

}
