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
} from "@/types"
import type { Repository, Scan, Finding } from "@/app/data"

const isLive = process.env.NEXT_PUBLIC_API_MODE === "live"

// When isLive, every function calls the real apiClient.
// Those paths are marked TODO(live) — backend dev fills them in.
// For now they fall through to mock so the UI never crashes.

export const api = {
  // ─── Auth ──────────────────────────────────────────────────────────────────
  login: (body: LoginRequest): Promise<AuthResponse> => {
    if (isLive) {
      // TODO(live): import { apiClient } from './client'; import { endpoints } from './endpoints'
      // return apiClient.post<AuthResponse>(endpoints.auth.login, body)
    }
    return mock.mockLogin(body)
  },

  register: (body: RegisterRequest): Promise<AuthResponse> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI
      // Endpoint: POST /api/auth/register; Request: RegisterRequest; Response: AuthResponse
    }
    return mock.mockRegister(body)
  },

  logout: (): Promise<void> => {
    if (isLive) {
      // TODO(live): return apiClient.post(endpoints.auth.logout)
    }
    return mock.mockLogout()
  },

  getSession: () => {
    if (isLive) {
      // TODO(live): return apiClient.get<User>(endpoints.users.me)
    }
    return mock.mockGetSession()
  },

  requestPasswordReset: (body: ResetRequest): Promise<void> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI
      // Endpoint: POST /api/auth/password-reset/request; Request: ResetRequest; Response: None
    }
    return mock.mockRequestPasswordReset(body)
  },

  confirmPasswordReset: (body: PasswordResetConfirm): Promise<void> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI
      // Endpoint: POST /api/auth/password-reset/confirm; Request: PasswordResetConfirm; Response: None
    }
    return mock.mockConfirmPasswordReset(body)
  },

  // ─── Users ─────────────────────────────────────────────────────────────────
  updateProfile: (body: ProfileUpdate) => {
    if (isLive) {
      // TODO(live): return apiClient.put<User>(endpoints.users.me, body)
    }
    return mock.mockUpdateProfile(body)
  },

  updatePassword: (body: PasswordUpdate): Promise<void> => {
    if (isLive) {
      // TODO(live): return apiClient.put(endpoints.users.password, body)
    }
    return mock.mockUpdatePassword(body)
  },


  // ─── Repositories ──────────────────────────────────────────────────────────
  getRepositories: (page = 1, page_size = 50): Promise<Paginated<Repository>> => {
    if (isLive) {
      // TODO(live): return apiClient.get<Paginated<Repository>>(endpoints.repositories.list, { params: { page, page_size } })
    }
    return mock.mockGetRepositories(page, page_size)
  },

  getRepository: (id: string): Promise<Repository> => {
    if (isLive) {
      // TODO(live): return apiClient.get<Repository>(endpoints.repositories.detail(id))
    }
    return mock.mockGetRepository(id)
  },

  getRepositoryBranches: (id: string): Promise<Branch[]> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI
      // Endpoint: GET /api/repositories/{id}/branches; Response: Branch[]
    }
    return mock.mockGetRepositoryBranches(id)
  },

  createRepository: (body: RepositoryCreate): Promise<Repository> => {
    if (isLive) {
      // TODO(live): return apiClient.post<Repository>(endpoints.repositories.list, body)
    }
    return mock.mockCreateRepository(body)
  },

  validateRepository: (body: RepositoryValidate): Promise<ValidateResponse> => {
    if (isLive) {
      // TODO(live): return apiClient.post<ValidateResponse>(endpoints.repositories.validate, body)
    }
    return mock.mockValidateRepository(body)
  },

  deleteRepository: (id: string): Promise<void> => {
    if (isLive) {
      // TODO(live): return apiClient.delete(endpoints.repositories.detail(id))
    }
    return mock.mockDeleteRepository(id)
  },


  // ─── Scans ─────────────────────────────────────────────────────────────────
  getScans: (page = 1, page_size = 50, repoId?: string): Promise<Paginated<Scan>> => {
    if (isLive) {
      // TODO(live): return apiClient.get<Paginated<Scan>>(endpoints.scans.list, { params: { page, page_size, repo_id: repoId } })
    }
    return mock.mockGetScans(page, page_size, repoId)
  },

  getScan: (id: string): Promise<Scan> => {
    if (isLive) {
      // TODO(live): return apiClient.get<Scan>(endpoints.scans.detail(id))
    }
    return mock.mockGetScan(id)
  },

  triggerScan: (body: ScanTrigger): Promise<Scan> => {
    if (isLive) {
      // TODO(live): return apiClient.post<Scan>(endpoints.scans.trigger, body)
    }
    return mock.mockTriggerScan(body)
  },

  getScanStatus: (id: string) => {
    if (isLive) {
      // TODO(live): return apiClient.get<ScanStatusResult>(endpoints.scans.status(id))
    }
    return mock.mockGetScanStatus(id)
  },

  cancelScan: (id: string): Promise<Scan> => {
    if (isLive) {
      // TODO(live): return apiClient.post<Scan>(endpoints.scans.cancel(id))
    }
    return mock.mockCancelScan(id)
  },

  getScanFindings: (scanId: string, query: FindingQuery = {}): Promise<Paginated<Finding>> => {
    if (isLive) {
      // TODO(live): return apiClient.get<Paginated<Finding>>(endpoints.scans.findings(scanId), { params: query })
    }
    return mock.mockGetScanFindings(scanId, query)
  },

  // ─── Findings ──────────────────────────────────────────────────────────────
  getFindings: (query: FindingQuery = {}): Promise<Paginated<Finding>> => {
    if (isLive) {
      // TODO(live): return apiClient.get<Paginated<Finding>>(endpoints.findings.list, { params: query })
    }
    return mock.mockGetFindings(query)
  },

  getFinding: (id: string): Promise<Finding> => {
    if (isLive) {
      // TODO(live): return apiClient.get<Finding>(endpoints.findings.detail(id))
    }
    return mock.mockGetFinding(id)
  },

  updateFinding: (id: string, body: FindingUpdate): Promise<Finding> => {
    if (isLive) {
      // TODO(live): return apiClient.patch<Finding>(endpoints.findings.detail(id), body)
    }
    return mock.mockUpdateFinding(id, body)
  },

  // ─── Reports ───────────────────────────────────────────────────────────────
  getReports: (page = 1, page_size = 50): Promise<Paginated<Scan>> => {
    if (isLive) {
      // TODO(live): return apiClient.get<Paginated<Report>>(endpoints.reports.list, { params: { page, page_size } })
    }
    return mock.mockGetReports(page, page_size)
  },

  getReport: (id: string): Promise<Report> => {
    if (isLive) {
      // TODO(live): return apiClient.get<Report>(endpoints.reports.detail(id))
    }
    return mock.mockGetReport(id)
  },

  generateReport: (body: ReportCreate): Promise<Report> => {
    if (isLive) {
      // TODO(live): return apiClient.post<Report>(endpoints.reports.generate, body)
    }
    return mock.mockGenerateReport(body)
  },

  downloadReportPdf: (id: string): Promise<Blob> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI. The back end will have the LLM write the report content and render it to PDF server-side; the front end only requests and downloads it.
      // Endpoint: GET /api/reports/{id}/pdf; Response: application/pdf
    }
    return mock.mockDownloadReportPdf(id)
  },

  // ─── Dashboard ─────────────────────────────────────────────────────────────
  getDashboard: (): Promise<DashboardMetrics> => {
    if (isLive) {
      // TODO(live): return apiClient.get<DashboardMetrics>(endpoints.dashboard.metrics)
    }
    return mock.mockGetDashboard()
  },

  // ─── GitHub Integration ────────────────────────────────────────────────────
  getGithubIntegration: (): Promise<GithubIntegration> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI
      // Endpoint: GET /api/integrations/github; Request: None; Response: GithubIntegration
    }
    return mock.mockGetGithubIntegration()
  },

  connectGithub: (body: GitHubConnect = {}): Promise<GithubIntegration> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI
      // Endpoint: POST /api/integrations/github; Request: GitHubConnect; Response: GithubIntegration
    }
    return mock.mockConnectGithub(body)
  },

  disconnectGithub: (): Promise<GithubIntegration> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI
      // Endpoint: DELETE /api/integrations/github; Request: None; Response: GithubIntegration
    }
    return mock.mockDisconnectGithub()
  },

  getSettings: (): Promise<UserSettings> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI
      // Endpoint: GET /api/users/me/settings; Request: None; Response: UserSettings
    }
    return mock.mockGetSettings()
  },

  updateSettings: (body: UserSettings): Promise<UserSettings> => {
    if (isLive) {
      // PLACEHOLDER: connect to FastAPI
      // Endpoint: PUT /api/users/me/settings; Request: UserSettings; Response: UserSettings
    }
    return mock.mockUpdateSettings(body)
  },

  // ─── Misc ──────────────────────────────────────────────────────────────────
  reset: (): Promise<void> => mock.mockReset(),

}
