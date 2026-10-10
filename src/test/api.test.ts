// Unit tests for the mock service layer (Phase A).
// These verify that mock adapters behave correctly before any component wiring.

import { describe, it, expect, beforeEach, vi } from "vitest"

// We need to stub localStorage before importing services
const mockStorage: Record<string, string> = {}
vi.stubGlobal("localStorage", {
  getItem: (key: string) => mockStorage[key] ?? null,
  setItem: (key: string, value: string) => { mockStorage[key] = value },
  removeItem: (key: string) => { delete mockStorage[key] },
  clear: () => { Object.keys(mockStorage).forEach((k) => delete mockStorage[k]) },
})
vi.stubGlobal("sessionStorage", {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
})

// Now import the api facade
import { api } from "@/lib/api"
import { getScanOutcome } from "@/types"

beforeEach(() => {
  // Clear storage between tests
  Object.keys(mockStorage).forEach((k) => delete mockStorage[k])
})

describe("auth", () => {
  it("registers and signs in a user", async () => {
    await api.register({ name: "New User", email: "new@example.com", password: "secure-pass" })
    expect((await api.getSession()).email).toBe("new@example.com")
  })
  it("login succeeds with correct demo credentials", async () => {
    const result = await api.login({
      email: "team.b@amalitechtraining.org",
      password: "demo-security",
    })
    expect(result.access_token).toBe("demo-token")
  })

  it("login throws with wrong credentials", async () => {
    await expect(
      api.login({ email: "wrong@example.com", password: "wrongpassword" }),
    ).rejects.toThrow()
  })

  it("getSession returns profile after login", async () => {
    await api.login({ email: "team.b@amalitechtraining.org", password: "demo-security" })
    const session = await api.getSession()
    expect(session.authenticated).toBe(true)
    expect(session.email).toBe("team.b@amalitechtraining.org")
  })
})

describe("repositories", () => {
  it("returns searchable branch metadata with a default", async () => {
    const branches = await api.getRepositoryBranches("web-app")
    expect(branches.some((branch) => branch.is_default)).toBe(true)
    expect(branches.length).toBeGreaterThan(1)
  })
  it("returns paginated repositories", async () => {
    const result = await api.getRepositories()
    expect(result.items.length).toBeGreaterThan(0)
    expect(typeof result.total).toBe("number")
    expect(result.page).toBe(1)
  })

  it("creates a new repository from a GitHub URL", async () => {
    const result = await api.createRepository({
      url: "https://github.com/testorg/my-repo",
    })
    expect(result.name).toBe("testorg/my-repo")
  })

  it("throws on invalid repository URL", async () => {
    await expect(
      api.createRepository({ url: "https://notgithub.com/repo" }),
    ).rejects.toThrow()
  })

  it("validates a valid repository URL", async () => {
    const result = await api.validateRepository({
      url: "https://github.com/testorg/my-repo",
    })
    expect(result.accessible).toBe(true)
  })
})

describe("scans", () => {
  it("triggers a scan and returns a queued scan", async () => {
    const repos = await api.getRepositories()
    const repoId = repos.items[0].id
    const scan = await api.triggerScan({ repo_id: repoId, branch: "develop" })
    expect(scan.status).toBe("Queued")
    expect(scan.repoId).toBe(repoId)
    expect(scan.branch).toBe("develop")
  })

  it("getScanStatus advances progress over time", async () => {
    const repos = await api.getRepositories()
    const repoId = repos.items[0].id
    const scan = await api.triggerScan({ repo_id: repoId, branch: "develop" })

    // Simulate 4 seconds elapsed by manipulating start time in storage
    const key = `rsa-scan-progress-${scan.id}`
    const oldTime = Date.now() - 4000
    mockStorage[key] = JSON.stringify(oldTime)

    const status = await api.getScanStatus(scan.id)
    expect(status.stage).toBeGreaterThan(0)
    expect(status.progress).toBeGreaterThan(0)
  })
})

describe("scan outcomes", () => {
  it("derives the system-owned outcome from status and findings", () => {
    expect(getScanOutcome({ status: "Queued" })).toBe("queued")
    expect(getScanOutcome({ status: "Completed", findings: 0 })).toBe("completed_clean")
    expect(getScanOutcome({ status: "Completed", findings: 2 })).toBe("completed_with_findings")
    expect(getScanOutcome({ status: "Failed" })).toBe("failed")
  })
})

describe("findings", () => {
  it("returns paginated findings", async () => {
    const result = await api.getFindings()
    expect(Array.isArray(result.items)).toBe(true)
  })

  it("updates a finding status", async () => {
    const findings = await api.getFindings()
    const first = findings.items[0]
    if (!first) return // seed data might be empty in isolated test

    const updated = await api.updateFinding(first.id, {
      status: "Reviewed",
      review_note: "Test note",
    })
    expect(updated.status).toBe("Reviewed")
  })
})

describe("reports", () => {
  it("returns only completed scans as reports", async () => {
    const result = await api.getReports()
    expect(result.items.every((s) => ["Completed", "Partial"].includes(s.status))).toBe(true)
  })
})

describe("dashboard", () => {
  it("returns dashboard metrics", async () => {
    const metrics = await api.getDashboard()
    expect(typeof metrics.total_repositories).toBe("number")
    expect(typeof metrics.critical_count).toBe("number")
    expect(Array.isArray(metrics.recent_scans)).toBe(true)
  })
})

describe("account settings", () => {
  it("persists GitHub integration and notification preferences through the API", async () => {
    await api.disconnectGithub()
    expect((await api.getGithubIntegration()).connected).toBe(false)
    await api.connectGithub()
    expect((await api.getGithubIntegration()).connected).toBe(true)

    await api.updateSettings({ completion: false, failure: true })
    expect(await api.getSettings()).toEqual({ completion: false, failure: true })
  })
})
