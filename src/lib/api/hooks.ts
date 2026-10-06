"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "./index"
import type {
  FindingQuery,
  LoginRequest,
  RegisterRequest,
  PasswordResetConfirm,
  ProfileUpdate,
  PasswordUpdate,
  RepositoryCreate,
  RepositoryValidate,
  ScanTrigger,
  FindingUpdate,
  ReportCreate,
  GitHubConnect,
  UserSettings,
} from "@/types"

export const queryKeys = {
  session: ["session"] as const,
  repositories: (page?: number, pageSize?: number) =>
    ["repositories", page, pageSize] as const,
  repository: (id: string) => ["repository", id] as const,
  repositoryBranches: (id: string) => ["repositoryBranches", id] as const,
  scans: (page?: number, pageSize?: number, repoId?: string) =>
    ["scans", page, pageSize, repoId] as const,
  scan: (id: string) => ["scan", id] as const,
  scanStatus: (id: string) => ["scanStatus", id] as const,
  scanFindings: (scanId: string, query: FindingQuery) =>
    ["scanFindings", scanId, query] as const,
  findings: (query: FindingQuery) => ["findings", query] as const,
  finding: (id: string) => ["finding", id] as const,
  reports: (page?: number, pageSize?: number) =>
    ["reports", page, pageSize] as const,
  report: (id: string) => ["report", id] as const,
  dashboard: ["dashboard"] as const,
  github: ["github"] as const,
  settings: ["settings"] as const,
}

// ─── Auth ──────────────────────────────────────────────────────────────────

export function useSession() {
  return useQuery({
    queryKey: queryKeys.session,
    queryFn: () => api.getSession(),
    retry: false, // Don't retry auth checks
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LoginRequest) => api.login(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.session })
    },
  })
}

export function useRegister() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: (body: RegisterRequest) => api.register(body), onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.session }) })
}

export function useRequestPasswordReset() {
  return useMutation({ mutationFn: (body: { email: string }) => api.requestPasswordReset(body) })
}

export function useConfirmPasswordReset() {
  return useMutation({ mutationFn: (body: PasswordResetConfirm) => api.confirmPasswordReset(body) })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      qc.clear()
    },
  })
}

// ─── Users ─────────────────────────────────────────────────────────────────

export function useUpdateProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ProfileUpdate) => api.updateProfile(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.session })
    },
  })
}

export function useUpdatePassword() {
  return useMutation({
    mutationFn: (body: PasswordUpdate) => api.updatePassword(body),
  })
}

// ─── Repositories ──────────────────────────────────────────────────────────

export function useRepositories(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: queryKeys.repositories(page, pageSize),
    queryFn: () => api.getRepositories(page, pageSize),
  })
}

export function useRepository(id: string) {
  return useQuery({
    queryKey: queryKeys.repository(id),
    queryFn: () => api.getRepository(id),
    enabled: !!id,
  })
}

export function useRepositoryBranches(repoId: string) {
  return useQuery({ queryKey: queryKeys.repositoryBranches(repoId), queryFn: () => api.getRepositoryBranches(repoId), enabled: !!repoId, retry: 1 })
}

export function useCreateRepository() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: RepositoryCreate) => api.createRepository(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.repositories() })
      qc.invalidateQueries({ queryKey: queryKeys.dashboard })
    },
  })
}

export function useValidateRepository() {
  return useMutation({
    mutationFn: (body: RepositoryValidate) => api.validateRepository(body),
  })
}

export function useDeleteRepository() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteRepository(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.repositories() })
      qc.invalidateQueries({ queryKey: queryKeys.dashboard })
    },
  })
}

// ─── Scans ─────────────────────────────────────────────────────────────────

export function useScans(page = 1, pageSize = 50, repoId?: string) {
  return useQuery({
    queryKey: queryKeys.scans(page, pageSize, repoId),
    queryFn: () => api.getScans(page, pageSize, repoId),
  })
}

export function useScan(id: string) {
  return useQuery({
    queryKey: queryKeys.scan(id),
    queryFn: () => api.getScan(id),
    enabled: !!id,
  })
}

export function useTriggerScan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ScanTrigger) => api.triggerScan(body),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: queryKeys.scans() })
      qc.invalidateQueries({ queryKey: queryKeys.dashboard })
      if (variables.repo_id) {
        qc.invalidateQueries({ queryKey: queryKeys.repository(variables.repo_id) })
      }
    },
  })
}

export function useScanStatus(id: string) {
  const qc = useQueryClient()
  return useQuery({
    queryKey: queryKeys.scanStatus(id),
    queryFn: () => api.getScanStatus(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 2000 // Poll every 2s initially
      // Stop polling if completed or failed
      const status = data.status.toLowerCase()
      if (["completed", "failed", "partial", "cancelled"].includes(status)) return false
      return 2000
    },
    // When a scan completes, invalidate related data
    // We can use a side effect inside the query or via the components.
    // For now, components will react to the status change.
  })
}

export function useCancelScan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.cancelScan(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.scan(id) })
      qc.invalidateQueries({ queryKey: queryKeys.scanStatus(id) })
      qc.invalidateQueries({ queryKey: queryKeys.scans() })
    },
  })
}

export function useScanFindings(scanId: string, query: FindingQuery = {}) {
  return useQuery({
    queryKey: queryKeys.scanFindings(scanId, query),
    queryFn: () => api.getScanFindings(scanId, query),
    enabled: !!scanId,
  })
}

// ─── Findings ──────────────────────────────────────────────────────────────

export function useFindings(query: FindingQuery = {}) {
  return useQuery({
    queryKey: queryKeys.findings(query),
    queryFn: () => api.getFindings(query),
  })
}

export function useFinding(id: string) {
  return useQuery({
    queryKey: queryKeys.finding(id),
    queryFn: () => api.getFinding(id),
    enabled: !!id,
  })
}

export function useUpdateFinding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: FindingUpdate }) =>
      api.updateFinding(id, body),
    onSuccess: (data, { id }) => {
      qc.invalidateQueries({ queryKey: queryKeys.finding(id) })
      qc.invalidateQueries({ queryKey: queryKeys.findings({}) })
      if (data.scanId) {
        qc.invalidateQueries({ queryKey: queryKeys.scanFindings(data.scanId, {}) })
      }
      qc.invalidateQueries({ queryKey: queryKeys.dashboard })
    },
  })
}

// ─── Reports ───────────────────────────────────────────────────────────────

export function useReports(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: queryKeys.reports(page, pageSize),
    queryFn: () => api.getReports(page, pageSize),
  })
}

export function useReport(id: string) {
  return useQuery({
    queryKey: queryKeys.report(id),
    queryFn: () => api.getReport(id),
    enabled: !!id,
    refetchInterval: (query) => query.state.data?.status === "generating" ? 1000 : false,
  })
}

export function useDownloadReportPdf() {
  return useMutation({ mutationFn: (id: string) => api.downloadReportPdf(id) })
}

export function useGenerateReport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReportCreate) => api.generateReport(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.reports() })
    },
  })
}

// ─── Dashboard ─────────────────────────────────────────────────────────────

export function useDashboard() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => api.getDashboard(),
  })
}

// ─── Integrations ──────────────────────────────────────────────────────────

export function useGitHubStatus() {
  return useQuery({
    queryKey: queryKeys.github,
    queryFn: () => api.getGithubIntegration(),
  })
}

export function useGitHubConnect() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: GitHubConnect = {}) => api.connectGithub(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.github })
    },
  })
}

export function useGitHubDisconnect() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.disconnectGithub(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.github })
    },
  })
}

export function useSettings() {
  return useQuery({ queryKey: queryKeys.settings, queryFn: () => api.getSettings() })
}

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: UserSettings) => api.updateSettings(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.settings }),
  })
}

// ─── Misc ──────────────────────────────────────────────────────────────────

export function useResetDemo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.reset(),
    onSuccess: () => {
      qc.clear()
    },
  })
}
