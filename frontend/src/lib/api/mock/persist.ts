// Mock persistence helpers for the API adapters.
// ALL localStorage usage for data (not theme) must live here and ONLY here.

import {
  repositories as seedRepos,
  scans as seedScans,
  findings as seedFindings,
  repositoryMetadata,
  type Repository,
  type Scan,
  type Finding,
  type FindingStatus,
} from "@/app/data"

const KEYS = {
  repos: "rsa-repos",
  scans: "rsa-scans",
  findings: "rsa-findings",
  auth: "rsa-auth",
  remember: "rsa-remember",
  profile: "rsa-profile",
  github: "rsa-github",
  settings: "rsa-settings",
  scanProgress: (id: string) => `rsa-scan-progress-${id}`,
} as const

function rebrandValue(field: string, value: unknown) {
  if (typeof value !== "string" || ["id", "repoId"].includes(field))
    return value
  return value
    .replace(/@acme\.dev/gi, "@amalitech.dev")
    .replace(/^alex@amalitech\.dev$/i, "team.b@amalitechtraining.org")
    .replace(/^Alex Lawson$/i, "Team B")
    .replace(/acme-demo-uploads/gi, "amalitech-demo-uploads")
    .replace(/\bacme\b/gi, "Amalitech")
}

function load<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback
  try {
    return (
      JSON.parse(localStorage.getItem(key) || "null", rebrandValue) ?? fallback
    )
  } catch {
    return fallback
  }
}

function save(key: string, value: unknown) {
  if (typeof window === "undefined") return
  localStorage.setItem(key, JSON.stringify(value))
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export function mockPersist_getAuth(): boolean {
  if (typeof window === "undefined") return true
  try {
    return (
      sessionStorage.getItem("rsa-auth") === "true" ||
      load<boolean>(KEYS.auth, false)
    )
  } catch {
    return true
  }
}

export function mockPersist_setAuth(authenticated: boolean, remember: boolean) {
  save(KEYS.auth, authenticated && remember)
  save(KEYS.remember, remember)
  if (typeof window !== "undefined") {
    if (authenticated) sessionStorage.setItem("rsa-auth", "true")
    else sessionStorage.removeItem("rsa-auth")
  }
}

export function mockPersist_getRemember(): boolean {
  return load<boolean>(KEYS.remember, true)
}

// ─── Profile ──────────────────────────────────────────────────────────────────

export interface MockProfile {
  name: string
  email: string
}

export const MOCK_LOGIN_EMAIL = "team.b@amalitechtraining.org"

export function mockPersist_getProfile(): MockProfile {
  return load(KEYS.profile, { name: "Team B", email: MOCK_LOGIN_EMAIL })
}

export function mockPersist_setProfile(profile: MockProfile) {
  save(KEYS.profile, profile)
}

// ─── Repositories ─────────────────────────────────────────────────────────────

export function mockPersist_getRepositories(): Repository[] {
  return load<Repository[]>(KEYS.repos, seedRepos).map(repositoryMetadata)
}

export function mockPersist_setRepositories(repos: Repository[]) {
  save(KEYS.repos, repos)
}

// ─── Scans ────────────────────────────────────────────────────────────────────

export function mockPersist_getScans(): Scan[] {
  const raw = load<Scan[]>(KEYS.scans, seedScans)
  const findings = mockPersist_getFindings()
  return raw.map((scan) => ({
    ...scan,
    findingsSnapshot:
      scan.findingsSnapshot ??
      findings
        .filter(
          (f) =>
            f.repoId === scan.repoId &&
            (!scan.findingIds || scan.findingIds.includes(f.id)),
        )
        .map((f) => ({ ...f, scanId: scan.id })),
  }))
}

export function mockPersist_setScans(scans: Scan[]) {
  save(KEYS.scans, scans)
}

// ─── Findings ─────────────────────────────────────────────────────────────────

export function mockPersist_getFindings(): Finding[] {
  return load<Finding[]>(KEYS.findings, seedFindings)
}

export function mockPersist_setFindings(findings: Finding[]) {
  save(KEYS.findings, findings)
}

export function mockPersist_setFindingStatus(
  id: string,
  status: FindingStatus,
  note?: string,
) {
  const findings = mockPersist_getFindings().map((f) =>
    f.id === id ? { ...f, status, reviewNote: note } : f,
  )
  mockPersist_setFindings(findings)
  return findings.find((f) => f.id === id)
}

// ─── GitHub integration ────────────────────────────────────────────────────────

export function mockPersist_getGitHubConnected(): boolean {
  return load(KEYS.github, null) !== false
}

export function mockPersist_setGitHubConnected(connected: boolean) {
  save(KEYS.github, connected)
}

export interface MockUserSettings {
  completion: boolean
  failure: boolean
}

export function mockPersist_getSettings(): MockUserSettings {
  return load(KEYS.settings, { completion: true, failure: true })
}

export function mockPersist_setSettings(settings: MockUserSettings) {
  save(KEYS.settings, settings)
}

// ─── Scan progress tracking ───────────────────────────────────────────────────
// The scan timer simulation is driven by wall-clock time so that polling the
// getScanStatus endpoint always returns consistent progress regardless of how
// often the UI polls.

export function mockPersist_getScanStartTime(scanId: string): number | null {
  return load<number | null>(KEYS.scanProgress(scanId), null)
}

export function mockPersist_setScanStartTime(scanId: string, time: number) {
  save(KEYS.scanProgress(scanId), time)
}

export function mockPersist_clearScanProgress(scanId: string) {
  if (typeof window !== "undefined") {
    localStorage.removeItem(KEYS.scanProgress(scanId))
  }
}

// ─── Reset ────────────────────────────────────────────────────────────────────

export function mockPersist_reset() {
  mockPersist_setRepositories(seedRepos)
  mockPersist_setScans(seedScans)
  mockPersist_setFindings(seedFindings)
  mockPersist_setProfile({ name: "Team B", email: MOCK_LOGIN_EMAIL })
  mockPersist_setGitHubConnected(true)
  mockPersist_setSettings({ completion: true, failure: true })
}
