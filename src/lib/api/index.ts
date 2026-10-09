import { apiClient, setAuthToken, getAuthToken } from "./client"
import { endpoints } from "./endpoints"
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
} from "@/types"
import type { Repository, Scan, Finding } from "@/app/data"

const isLive = process.env.NEXT_PUBLIC_API_MODE === "live"

function capitalize(str: string): string {
  if (!str) return ""
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

// ─── Data Adapters (Maps live FastAPI models to Frontend UI types) ───────────

function adaptRepository(r: any): Repository {
  if (!r) return r
  return {
    id: r.id,
    name: r.name || (r.url ? r.url.split("/").slice(-2).join("/") : "repository"),
    owner: r.owner || (r.url ? r.url.split("/").slice(-2)[0] : "owner"),
    url: r.url || `https://github.com/${r.name}`,
    branch: r.defaultBranch || r.default_branch || r.branch || "main",
    description: r.description || "Connected GitHub repository",
    language: r.language || "Public Repository",
    commit: r.commit || "HEAD",
    visibility: r.visibility || "Public",
    connected: r.createdAt
      ? new Date(r.createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })
      : "Recently",
    access: "granted",
  }
}

function adaptScan(s: any): Scan {
  if (!s) return s
  const dateObj = s.createdAt ? new Date(s.createdAt) : new Date()
  const formattedDate = dateObj.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })

  let durationText = "In progress"
  if (s.completedAt && s.startedAt) {
    const diffSec = Math.max(1, Math.round((new Date(s.completedAt).getTime() - new Date(s.startedAt).getTime()) / 1000))
    durationText = `${diffSec}s`
  } else if (s.status === "completed") {
    durationText = "3s"
  }

  const rawStatus = (s.status || "queued").toLowerCase()
  const capitalizedStatus = capitalize(rawStatus)

  return {
    id: s.id,
    repoId: s.repositoryId || s.repository_id || s.repoId,
    status: capitalizedStatus as any,
    date: formattedDate,
    relative: "Recently",
    duration: durationText,
    progress: s.progress ?? (rawStatus === "completed" ? 100 : 0),
    stage: rawStatus === "completed" ? 4 : rawStatus === "running" ? 2 : 1,
    branch: s.branch || "main",
    findingsCount: s.findingsCount,
    startedAt: s.startedAt,
    completedAt: s.completedAt,
  }
}

function adaptFinding(f: any): Finding {
  if (!f) return f
  const rawSev = (f.severity || "medium").toLowerCase()
  const rawConf = (f.confidence || "high").toLowerCase()
  
  // Align backend taxonomy strings to exact frontend enum values
  let cat: any = "Code"
  const rawCat = (f.category || "").toLowerCase()
  if (rawCat.includes("secret") || rawCat.includes("key") || rawCat.includes("token")) {
    cat = "Secrets"
  } else if (rawCat.includes("dependency") || rawCat.includes("package") || rawCat.includes("cve")) {
    cat = "Dependencies"
  } else if (rawCat.includes("config") || rawCat.includes("insecure configuration")) {
    cat = "Configuration"
  }

  let statusText: any = "Open"
  if (f.reviewStatus === "acknowledged" || f.review_status === "acknowledged") statusText = "Reviewed"
  else if (f.reviewStatus === "false_positive" || f.review_status === "false_positive") statusText = "False positive"
  else if (f.reviewStatus === "resolved" || f.review_status === "resolved") statusText = "Resolved"

  return {
    id: f.id,
    repoId: f.repositoryId || f.repository_id || f.repoId,
    title: f.title || "Security Finding",
    severity: capitalize(rawSev) as any,
    category: cat,
    confidence: capitalize(rawConf) as any,
    file: f.filePath || f.file_path || f.file || "unknown",
    line: f.lineStart || f.line_start || f.line || 1,
    scanner: f.category || "Security Check",
    rule: f.category || "Rule",
    status: statusText,
    description: f.description,
    recommendation: f.recommendation,
    aiExplanation: f.aiExplanation || f.ai_explanation,
    codeSnippet: f.codeSnippet || f.code_snippet,
  }
}

// ─── API Service Object ──────────────────────────────────────────────────────

export const api = {
  // Auth
  login: async (body: LoginRequest): Promise<AuthResponse> => {
    if (isLive) {
      const res = await apiClient.post<any>(endpoints.auth.login, body)
      if (res && res.token) {
        setAuthToken(res.token, res.user)
      }
      return res
    }
    return mock.mockLogin(body)
  },

  register: async (body: RegisterRequest): Promise<AuthResponse> => {
    if (isLive) {
      const res = await apiClient.post<any>(endpoints.auth.register, body)
      if (res && res.token) {
        setAuthToken(res.token, res.user)
      }
      return res
    }
    return mock.mockRegister(body)
  },

  logout: async (): Promise<void> => {
    if (isLive) {
      try {
        await apiClient.post(endpoints.auth.logout)
      } catch {}
      setAuthToken(null)
      return
    }
    return mock.mockLogout()
  },

  getSession: async () => {
    if (isLive) {
      const token = getAuthToken()
      if (!token) return null
      try {
        const user = await apiClient.get<any>(endpoints.users.me)
        if (!user) return null
        return {
          authenticated: true,
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
          createdAt: user.createdAt,
          updatedAt: user.updatedAt,
          user: user,
          token: token,
        }
      } catch (err) {
        setAuthToken(null)
        return null
      }
    }
    return mock.mockGetSession()
  },

  requestPasswordReset: (body: ResetRequest): Promise<void> => {
    if (isLive) return apiClient.post(endpoints.auth.passwordResetRequest, body)
    return mock.mockRequestPasswordReset(body)
  },

  confirmPasswordReset: (body: PasswordResetConfirm): Promise<void> => {
    if (isLive) return apiClient.post(endpoints.auth.passwordResetConfirm, body)
    return mock.mockConfirmPasswordReset(body)
  },

  // Users
  updateProfile: (body: ProfileUpdate) => {
    if (isLive) return apiClient.put(endpoints.users.me, body)
    return mock.mockUpdateProfile(body)
  },

  updatePassword: (body: PasswordUpdate): Promise<void> => {
    if (isLive) return apiClient.put(endpoints.users.password, body)
    return mock.mockUpdatePassword(body)
  },

  // Repositories
  getRepositories: async (page = 1, page_size = 50): Promise<Paginated<Repository>> => {
    if (isLive) {
      const res = await apiClient.get<any>(endpoints.repositories.list, {
        params: { page, pageSize: page_size },
      })
      const items = (res.data || res.items || res || []).map(adaptRepository)
      return {
        items,
        total: res.total || items.length,
        page,
        page_size,
      }
    }
    return mock.mockGetRepositories(page, page_size)
  },

  getRepository: async (id: string): Promise<Repository> => {
    if (isLive) {
      const res = await apiClient.get<any>(endpoints.repositories.detail(id))
      return adaptRepository(res)
    }
    return mock.mockGetRepository(id)
  },

  getRepositoryBranches: async (id: string): Promise<Branch[]> => {
    if (isLive) {
      const res = await apiClient.get<any[]>(endpoints.repositories.branches(id))
      return (res || []).map((b: any) => ({
        name: b.name,
        isDefault: b.isDefault || b.is_default || false,
        is_default: b.isDefault || b.is_default || false,
        lastCommit: b.lastCommit || b.last_commit || "HEAD",
      }))
    }
    return mock.mockGetRepositoryBranches(id)
  },

  createRepository: async (body: RepositoryCreate): Promise<Repository> => {
    if (isLive) {
      const res = await apiClient.post<any>(endpoints.repositories.list, body)
      return adaptRepository(res)
    }
    return mock.mockCreateRepository(body)
  },

  validateRepository: (body: RepositoryValidate): Promise<ValidateResponse> => {
    if (isLive) {
      return apiClient.post<ValidateResponse>(endpoints.repositories.validate, body)
    }
    return mock.mockValidateRepository(body)
  },

  deleteRepository: (id: string): Promise<void> => {
    if (isLive) return apiClient.delete(endpoints.repositories.detail(id))
    return mock.mockDeleteRepository(id)
  },

  // Scans
  getScans: async (page = 1, page_size = 50, repoId?: string): Promise<Paginated<Scan>> => {
    if (isLive) {
      const res = await apiClient.get<any>(endpoints.scans.list, {
        params: { page, pageSize: page_size, repositoryId: repoId },
      })
      const items = (res.data || res.items || res || []).map(adaptScan)
      return {
        items,
        total: res.total || items.length,
        page,
        page_size,
      }
    }
    return mock.mockGetScans(page, page_size, repoId)
  },

  getScan: async (id: string): Promise<Scan> => {
    if (isLive) {
      const res = await apiClient.get<any>(endpoints.scans.detail(id))
      return adaptScan(res)
    }
    return mock.mockGetScan(id)
  },

  triggerScan: async (body: ScanTrigger): Promise<Scan> => {
    if (isLive) {
      const res = await apiClient.post<any>(endpoints.scans.trigger, {
        repositoryId: body.repositoryId || (body as any).repoId || (body as any).repository_id,
        branch: body.branch || "main",
      })
      return adaptScan(res)
    }
    return mock.mockTriggerScan(body)
  },

  getScanStatus: (id: string) => {
    if (isLive) return apiClient.get(endpoints.scans.status(id))
    return mock.mockGetScanStatus(id)
  },

  cancelScan: async (id: string): Promise<Scan> => {
    if (isLive) {
      const res = await apiClient.post<any>(endpoints.scans.cancel(id))
      return adaptScan(res)
    }
    return mock.mockCancelScan(id)
  },

  getScanFindings: async (scanId: string, query: FindingQuery = {}): Promise<Paginated<Finding>> => {
    if (isLive) {
      const res = await apiClient.get<any>(endpoints.scans.findings(scanId), { params: query as any })
      const items = (res.data || res.items || res || []).map(adaptFinding)
      return {
        items,
        total: res.total || items.length,
        page: 1,
        page_size: 1000,
      }
    }
    return mock.mockGetScanFindings(scanId, query)
  },

  // Findings
  getFindings: async (query: FindingQuery = {}): Promise<Paginated<Finding>> => {
    if (isLive) {
      const res = await apiClient.get<any>(endpoints.findings.list, { params: query as any })
      const items = (res.data || res.items || res || []).map(adaptFinding)
      return {
        items,
        total: res.total || items.length,
        page: 1,
        page_size: 1000,
      }
    }
    return mock.mockGetFindings(query)
  },

  getFinding: async (id: string): Promise<Finding> => {
    if (isLive) {
      const res = await apiClient.get<any>(endpoints.findings.detail(id))
      return adaptFinding(res)
    }
    return mock.mockGetFinding(id)
  },

  updateFinding: async (id: string, body: FindingUpdate): Promise<Finding> => {
    if (isLive) {
      const res = await apiClient.patch<any>(endpoints.findings.detail(id), body)
      return adaptFinding(res)
    }
    return mock.mockUpdateFinding(id, body)
  },

  // Reports
  getReports: (page = 1, page_size = 50): Promise<Paginated<Scan>> => {
    if (isLive) {
      return apiClient.get<Paginated<Scan>>(endpoints.reports.list, {
        params: { page, pageSize: page_size },
      })
    }
    return mock.mockGetReports(page, page_size)
  },

  getReport: (id: string): Promise<Report> => {
    if (isLive) return apiClient.get<Report>(endpoints.reports.detail(id))
    return mock.mockGetReport(id)
  },

  generateReport: (body: ReportCreate): Promise<Report> => {
    if (isLive) return apiClient.post<Report>(endpoints.reports.generate, body)
    return mock.mockGenerateReport(body)
  },

  downloadReportPdf: (id: string): Promise<Blob> => {
    if (isLive) return apiClient.getBlob(endpoints.reports.pdf(id))
    return mock.mockDownloadReportPdf(id)
  },

  // Dashboard
  getDashboard: (): Promise<DashboardMetrics> => {
    if (isLive) return apiClient.get<DashboardMetrics>(endpoints.dashboard.metrics)
    return mock.mockGetDashboard()
  },

  // Integrations
  getGithubIntegration: (): Promise<GithubIntegration> => {
    if (isLive) return apiClient.get<GithubIntegration>(endpoints.integrations.github)
    return mock.mockGetGithubIntegration()
  },

  connectGithub: (body: GitHubConnect = {}): Promise<GithubIntegration> => {
    if (isLive) return apiClient.post<GithubIntegration>(endpoints.integrations.github, body)
    return mock.mockConnectGithub(body)
  },

  disconnectGithub: (): Promise<GithubIntegration> => {
    if (isLive) return apiClient.delete<GithubIntegration>(endpoints.integrations.github)
    return mock.mockDisconnectGithub()
  },

  getSettings: (): Promise<UserSettings> => {
    if (isLive) return apiClient.get<UserSettings>(endpoints.users.settings)
    return mock.mockGetSettings()
  },

  updateSettings: (body: UserSettings): Promise<UserSettings> => {
    if (isLive) return apiClient.put<UserSettings>(endpoints.users.settings, body)
    return mock.mockUpdateSettings(body)
  },

  reset: (): Promise<void> => mock.mockReset(),
}
