"use client"

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"
import { toast } from "sonner"
import {
  findings as initialFindings,
  repositories as initialRepositories,
  scans as initialScans,
  createDemoFindings,
  getScanFindings,
  getFindingContext,
  repositoryMetadata,
  type DemoOutcome,
  type Finding,
  type FindingStatus,
  type Repository,
  type Scan,
} from "./data"

export const DEMO_LOGIN_EMAIL = "team.b@amalitechtraining.org"

type Profile = {
  name: string
  email: string
}
type Store = {
  repositories: Repository[]
  findings: Finding[]
  scans: Scan[]
  authenticated: boolean
  profile: Profile
  setProfile: (profile: Profile) => void
  role: string
  setRole: (role: string) => void
  login: (remember?: boolean) => void
  logout: () => void
  addRepository: (repo: Repository) => void
  startScan: (repoId: string, outcome?: DemoOutcome) => string
  retryScan: (id: string) => string
  isRestricted: (repoId?: string, scanId?: string) => boolean
  setRepositoryAccess: (repoId: string, granted: boolean) => void
  setFindingStatus: (id: string, status: FindingStatus, note?: string) => void
  reset: () => void
}
const StoreContext = createContext<Store | null>(null)
function rebrandValue(field: string, value: unknown) {
  if (typeof value !== "string" || ["id", "repoId"].includes(field))
    return value
  return value
    .replace(/@acme\.dev/gi, "@amalitech.dev")
    .replace(/^alex@amalitech\.dev$/i, DEMO_LOGIN_EMAIL)
    .replace(/^Alex Lawson$/i, "Team B")
    .replace(/acme-demo-uploads/gi, "amalitech-demo-uploads")
    .replace(/\bacme\b/gi, "Amalitech")
}
function updateBrand<Type>(value: Type): Type {
  const serialized = JSON.stringify(value)
  const updated = JSON.parse(serialized, rebrandValue)
  return JSON.stringify(updated) === serialized ? value : updated
}
function restore<Type>(key: string, fallback: Type): Type {
  if (typeof window === "undefined") return fallback
  try {
    return (
      JSON.parse(localStorage.getItem(`rsa-${key}`) || "null", rebrandValue) ??
      fallback
    )
  } catch {
    return fallback
  }
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [repositories, setRepositories] = useState(() =>
    restore("repos", initialRepositories).map(repositoryMetadata),
  )
  const [findings, setFindings] = useState(() =>
    restore("findings", initialFindings),
  )
  const [scans, setScans] = useState<Scan[]>(() =>
    restore("scans", initialScans).map((scan) => ({
      ...scan,
      findingsSnapshot:
        scan.findingsSnapshot ??
        findings
          .filter(
            (finding) =>
              finding.repoId === scan.repoId &&
              (!scan.findingIds || scan.findingIds.includes(finding.id)),
          )
          .map((finding) => ({ ...finding, scanId: scan.id })),
    })),
  )
  const [authenticated, setAuthenticated] = useState<boolean>(() => {
    if (typeof window === "undefined") return true
    try {
      return (
        sessionStorage.getItem("rsa-auth") === "true" ||
        restore<boolean>("auth", true)
      )
    } catch {
      return true
    }
  })
  const [remember, setRemember] = useState(() =>
    restore<boolean>("remember", true),
  )
  const [role, setRole] = useState(() => restore("role", "Developer"))
  const [profile, setProfile] = useState(() =>
    restore("profile", { name: "Team B", email: DEMO_LOGIN_EMAIL }),
  )
  useEffect(() => {
    setRepositories((current) => updateBrand(current))
    setFindings((current) => updateBrand(current))
    setProfile((current) => updateBrand(current))
  }, [])
  useEffect(() => {
    localStorage.setItem("rsa-repos", JSON.stringify(repositories))
  }, [repositories])
  useEffect(() => {
    localStorage.setItem("rsa-findings", JSON.stringify(findings))
  }, [findings])
  useEffect(() => {
    localStorage.setItem("rsa-scans", JSON.stringify(scans))
  }, [scans])
  useEffect(() => {
    localStorage.setItem("rsa-auth", JSON.stringify(authenticated && remember))
    localStorage.setItem("rsa-remember", JSON.stringify(remember))
    if (authenticated) sessionStorage.setItem("rsa-auth", "true")
    else sessionStorage.removeItem("rsa-auth")
  }, [authenticated, remember])
  useEffect(() => {
    localStorage.setItem("rsa-role", JSON.stringify(role))
  }, [role])
  useEffect(() => {
    localStorage.setItem("rsa-profile", JSON.stringify(profile))
  }, [profile])
  useEffect(() => {
    const timer = setInterval(
      () =>
        setScans((current) =>
          !current.some(
            (scan) => scan.isNew && ["Running", "Queued"].includes(scan.status),
          )
            ? current
            : current.map((scan) => {
                if (
                  !scan.isNew ||
                  (scan.status !== "Running" && scan.status !== "Queued")
                )
                  return scan
                const stage = Math.min(scan.stage + 1, 10)
                if (scan.outcome === "Failed" && stage >= 2) {
                  return {
                    ...scan,
                    status: "Failed",
                    stage: 1,
                    progress: 10,
                    duration: "4s (demo)",
                    relative: "Just now",
                    completedAt: new Date().toISOString(),
                  }
                }
                return {
                  ...scan,
                  stage,
                  progress: stage * 10,
                  status:
                    stage === 10
                      ? scan.outcome === "Partial"
                        ? "Partial"
                        : "Completed"
                      : "Running",
                  duration: stage === 10 ? "20s (demo)" : "In progress",
                  relative: stage === 10 ? "Just now" : "Running",
                  completedAt:
                    stage === 10 ? new Date().toISOString() : undefined,
                }
              }),
        ),
      2000,
    )
    return () => clearInterval(timer)
  }, [])
  useEffect(() => {
    const completed = scans.filter(
      (scan) => scan.isNew && ["Completed", "Partial"].includes(scan.status),
    )
    setFindings((current) => {
      const known = new Set(current.map((finding) => finding.id))
      const added = completed
        .flatMap((scan) => getScanFindings(scan, current))
        .filter((finding) => {
          if (known.has(finding.id)) return false
          known.add(finding.id)
          return true
        })
      return added.length ? [...current, ...added] : current
    })
  }, [scans])
  function isRestricted(repoId?: string, scanId?: string) {
    const target = repoId || scans.find((scan) => scan.id === scanId)?.repoId
    return repositories.some(
      (repo) => repo.id === target && repo.access === "denied",
    )
  }
  function enqueueScan(
    repoId: string,
    outcome: DemoOutcome = "Completed",
    source?: Scan,
  ) {
    const repo = repositories.find((repository) => repository.id === repoId)
    if (!authenticated || !repo || repo.access === "denied")
      throw new Error("You do not have permission to scan this repository.")
    if (
      typeof window !== "undefined" &&
      localStorage.getItem("rsa-github") === "false"
    )
      throw new Error(
        "Restore the demo GitHub connection before starting a scan.",
      )
    const continueQueued = source?.status === "Queued" && !source.isNew
    const id = continueQueued
      ? source.id
      : String(Math.max(12, ...scans.map((scan) => Number(scan.id))) + 1)
    const started = new Date()
    const partialRetry = source?.status === "Partial"
    const candidates =
      outcome === "No findings"
        ? []
        : partialRetry && source?.findingsSnapshot
          ? source.findingsSnapshot.map((finding) => ({
              ...finding,
              scanId: id,
            }))
          : createDemoFindings(repo, findings, id)
    const preserved = partialRetry ? getScanFindings(source, findings) : []
    const captured = [
      ...preserved.map((finding) => ({ ...finding, scanId: id })),
      ...candidates.filter(
        (finding) => !preserved.some((previous) => previous.id === finding.id),
      ),
    ]
    const job: Scan = {
      id,
      repoId,
      status: partialRetry ? "Running" : "Queued",
      date: `${started.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })} · ${started.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" })}`,
      relative: "Just now",
      duration: "—",
      progress: partialRetry ? 50 : 0,
      stage: partialRetry ? 5 : 0,
      isNew: true,
      commit: source?.commit || repo.commit,
      partialRetry,
      retryOf: continueQueued ? undefined : source?.id,
      outcome,
      findingsSnapshot: structuredClone(
        captured.map((finding) => ({
          ...finding,
          context: getFindingContext(finding),
        })),
      ),
      findingIds: captured.map((finding) => finding.id),
      startedAt: started.toISOString(),
    }
    setScans((current) => [job, ...current.filter((scan) => scan.id !== id)])
    return id
  }
  function startScan(repoId: string, outcome: DemoOutcome = "Completed") {
    return enqueueScan(repoId, outcome)
  }
  function retryScan(id: string) {
    const source = scans.find((scan) => scan.id === id)
    if (!source) throw new Error("This scan is not available.")
    const nextId = enqueueScan(source.repoId, "Completed", source)
    toast.success("Demo scan queued", {
      description: "Available evidence is preserved while the scan runs.",
    })
    return nextId
  }
  const visibleRepositories = repositories.filter(
    (repo) => repo.access !== "denied",
  )
  const visibleIds = new Set(visibleRepositories.map((repo) => repo.id))
  const value: Store = {
    repositories: visibleRepositories,
    findings: findings.filter((finding) => visibleIds.has(finding.repoId)),
    scans: scans.filter((scan) => visibleIds.has(scan.repoId)),
    authenticated,
    profile,
    setProfile,
    role,
    setRole,
    login: (remember = true) => {
      setRemember(remember)
      setAuthenticated(true)
    },
    logout: () => setAuthenticated(false),
    addRepository: (repo) =>
      setRepositories((current) =>
        current.some(
          (item) =>
            item.id === repo.id ||
            item.name.toLowerCase() === repo.name.toLowerCase(),
        )
          ? current
          : [...current, repositoryMetadata(repo)],
      ),
    startScan,
    retryScan,
    isRestricted,
    setRepositoryAccess: (repoId, granted) =>
      setRepositories((current) =>
        current.map((repo) =>
          repo.id === repoId
            ? { ...repo, access: granted ? "granted" : "denied" }
            : repo,
        ),
      ),
    setFindingStatus: (id, status, note) => {
      setFindings((current) =>
        current.map((finding) =>
          finding.id === id
            ? { ...finding, status, reviewNote: note }
            : finding,
        ),
      )
      toast.success(`Finding marked as ${status.toLowerCase()}`)
    },
    reset: () => {
      setRepositories(initialRepositories)
      setFindings(initialFindings)
      setScans(initialScans)
      setRole("Developer")
      setProfile({ name: "Team B", email: DEMO_LOGIN_EMAIL })
      toast.success("Demo workspace reset")
    },
  }
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}
export function useStore() {
  const store = useContext(StoreContext)
  if (!store) throw new Error("Store provider missing")
  return store
}
