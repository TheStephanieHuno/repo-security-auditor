"use client"

import { useState } from "react"
import { Link, useNavigate, useParams, useSearchParams } from "@/lib/router"
import {
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Code2,
  GitBranch,
  GitCommitHorizontal,
  Github,
  Loader2,
  LockKeyhole,
  MoreHorizontal,
  Play,
  Plus,
  ShieldCheck,
} from "lucide-react"
import { toast } from "sonner"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import {
  getRepositoryFindings,
  getScanFindings,
  scannerInfo,
  severityOrder,
  type Repository,
} from "./data"
import {
  Breadcrumbs,
  Confidence,
  EmptyState,
  Heading,
  LinkButton,
  Notice,
  PageHeader,
  PageState,
  AccessDenied,
  Panel,
  PanelHeader,
  RepoIdentity,
  RepositoryCard,
  ScanDialog,
  SearchInput,
  SeverityBadge,
  SeverityDistribution,
  StatusBadge,
} from "./components"
import { useStore } from "./store"

export function RepositoryList() {
  const { repositories, scans, findings } = useStore()
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState("All repositories")
  const [selected, setSelected] = useState<Repository>()
  const [scanOpen, setScanOpen] = useState(false)
  const [more, setMore] = useState<Repository>()
  if (!repositories.length)
    return (
      <PageState kind="Repositories">
        <PageHeader
          title="Repositories"
          description="Repositories connected to Repo Security Auditor."
        />
        <Panel>
          <EmptyState
            title="No repositories connected yet"
            description="Submit a GitHub repository to begin your first security review."
            action={
              <LinkButton to="/repositories/new" variant="default">
                Connect repository
              </LinkButton>
            }
          />
        </Panel>
      </PageState>
    )
  const list = repositories.filter((repo) => {
    const count = getRepositoryFindings(repo.id, scans, findings).filter(
      (findingRecord) => findingRecord.status === "Open",
    ).length
    return (
      repo.name.toLowerCase().includes(search.toLowerCase()) &&
      (filter === "All repositories" ||
        (filter === "Needs attention" && count > 0) ||
        (filter === "No open findings" && count === 0) ||
        (filter === "Recently scanned" &&
          scans.some(
            (scan) => scan.repoId === repo.id && scan.date.startsWith("Oct 1"),
          )))
    )
  })
  return (
    <PageState kind="Repositories">
      <PageHeader
        title="Repositories"
        description="Your codebases. Their security context. All in one place."
        eyebrow="REPOSITORY INVENTORY"
      >
        <LinkButton to="/repositories/new" variant="default">
          <Plus className="size-4" />
          Add repository
        </LinkButton>
      </PageHeader>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex max-w-full flex-wrap gap-1 rounded-lg border bg-background p-1">
          {[
            "All repositories",
            "Needs attention",
            "No open findings",
            "Recently scanned",
          ].map((item) => (
            <Button
              key={item}
              variant="ghost"
              aria-pressed={filter === item}
              className={cn(
                "h-7 px-3 text-xs",
                filter === item && "bg-muted font-medium",
              )}
              onClick={() => setFilter(item)}
            >
              {item}
              {item === "All repositories" && (
                <span className="ml-1 text-muted-foreground">
                  {repositories.length}
                </span>
              )}
            </Button>
          ))}
        </div>
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search repositories…"
          className="w-full sm:w-64"
        />
      </div>
      <Panel className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow className="bg-canvas">
              <TableHead className="pl-5 text-xs">Repository</TableHead>
              <TableHead className="text-xs">Branch</TableHead>
              <TableHead className="text-xs">Last scan</TableHead>
              <TableHead className="text-xs">Findings</TableHead>
              <TableHead className="text-xs">Scan status</TableHead>
              <TableHead className="pr-5 text-right text-xs">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.map((repo) => {
              const latest = scans.find((scan) => scan.repoId === repo.id)
              const repoFindings = getRepositoryFindings(
                repo.id,
                scans,
                findings,
              ).filter((findingRecord) => findingRecord.status === "Open")
              const highest = severityOrder.find((severity) =>
                repoFindings.some(
                  (findingRecord) => findingRecord.severity === severity,
                ),
              )
              return (
                <TableRow key={repo.id}>
                  <TableCell className="py-5 pl-5">
                    <RepoIdentity repo={repo} subtitle />
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
                      <GitBranch className="size-3" />
                      {repo.branch}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {latest?.relative || "Not scanned"}
                  </TableCell>
                  <TableCell>
                    <span className="mr-2 font-medium tabular-nums">
                      {repoFindings.length}
                    </span>
                    {highest ? (
                      <SeverityBadge severity={highest} />
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {latest ? (
                      <StatusBadge status={latest.status} />
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        Not scanned
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="pr-5">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="outline"
                        className="h-7 text-xs"
                        onClick={() => {
                          setSelected(repo)
                          setScanOpen(true)
                        }}
                      >
                        <Play className="size-3" />
                        Scan
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Actions for ${repo.name}`}
                        onClick={() => setMore(repo)}
                      >
                        <MoreHorizontal className="size-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
        {list.length === 0 && (
          <EmptyState
            title="No repositories match your filters"
            description="Try a different repository name or clear the active filter."
            action={
              <Button
                variant="outline"
                onClick={() => {
                  setSearch("")
                  setFilter("All repositories")
                }}
              >
                Clear filters
              </Button>
            }
          />
        )}
      </Panel>
      <div className="grid gap-4 sm:grid-cols-2 md:hidden">
        {list.map((repo) => (
          <div key={repo.id}>
            <RepositoryCard repo={repo} />
            <Button
              variant="outline"
              className="mt-2 w-full"
              onClick={() => {
                setSelected(repo)
                setScanOpen(true)
              }}
            >
              <Play className="size-3" />
              Start scan
            </Button>
          </div>
        ))}
        {list.length === 0 && (
          <EmptyState
            title="No repositories match"
            description="Try a different search or filter."
          />
        )}
      </div>
      <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {list.length} of {repositories.length} repositories
        </span>
        <span className="flex items-center gap-1.5">
          <Github className="size-3.5" />
          Connected via GitHub
        </span>
      </div>
      <ScanDialog
        key={selected?.id}
        repo={selected}
        open={scanOpen}
        onOpenChange={setScanOpen}
      />
      <Dialog
        open={!!more}
        onOpenChange={(open) => !open && setMore(undefined)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{more?.name}</DialogTitle>
            <DialogDescription>Repository actions</DialogDescription>
          </DialogHeader>
          <LinkButton to={`/repositories/${more?.id}`}>
            View repository
            <ArrowRight className="size-3" />
          </LinkButton>
          {scans.find(
            (scanRecord) =>
              scanRecord.repoId === more?.id &&
              scanRecord.status === "Completed",
          ) && (
            <LinkButton
              to={`/reports/${scans.find((scanRecord) => scanRecord.repoId === more?.id && scanRecord.status === "Completed")?.id}`}
            >
              View latest report
            </LinkButton>
          )}
          <Button
            variant="outline"
            onClick={() => {
              setSelected(more)
              setMore(undefined)
              setScanOpen(true)
            }}
          >
            <Play className="size-3" />
            Start scan
          </Button>
        </DialogContent>
      </Dialog>
    </PageState>
  )
}

const validationMessages: Record<string, [string, string]> = {
  invalid: [
    "Enter a valid GitHub repository URL.",
    "Use the format https://github.com/organization/repository.",
  ],
  missing: [
    "We couldn't find this repository.",
    "Check the owner and repository name, then try again.",
  ],
  denied: [
    "You do not have permission to access this repository.",
    "Ask the repository owner to grant access to your GitHub account.",
  ],
  unsupported: [
    "This repository type is not currently supported.",
    "This demo supports Python, JavaScript, TypeScript, and Terraform projects.",
  ],
  offline: [
    "We couldn't connect to GitHub. Try again.",
    "Check your connection. Your existing repositories remain available.",
  ],
}
export function AddRepository() {
  const store = useStore()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [url, setUrl] = useState("")
  const [state, setState] = useState("idle")
  const [preview, setPreview] = useState<Repository>()
  const [scenario, setScenario] = useState(params.get("state") || "success")
  const [github, setGithub] = useState(false)
  const [permissionConfirmed, setPermissionConfirmed] = useState(false)
  function validate() {
    const match = url
      .trim()
      .match(/^https:\/\/github\.com\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/)
    if (!match) {
      setState("invalid")
      return
    }
    setState("loading")
    setTimeout(() => {
      if (["missing", "denied", "unsupported", "offline"].includes(scenario)) {
        setState(scenario)
        return
      }
      const name = `${match[1]}/${match[2]}`
      const existing = store.repositories.find(
        (repo) => repo.name.toLowerCase() === name.toLowerCase(),
      )
      setPreview(
        existing || {
          id: `${match[1]}-${match[2]}-${crypto.randomUUID().slice(0, 8)}`.toLowerCase(),
          owner: match[1],
          url: `https://github.com/${name}`,
          name,
          description: "Newly connected GitHub repository",
          language: "TypeScript",
          branch: "main",
          commit: "f4a20b8",
          visibility: "Private",
          connected: new Date().toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
            timeZone: "UTC",
          }),
        },
      )
      setState("success")
    }, 1000)
  }
  return (
    <>
      <Breadcrumbs
        items={[
          { label: "Repositories", to: "/repositories" },
          { label: "Connect repository" },
        ]}
      />
      <PageHeader
        title="Connect repository"
        description="Bring your code into focus. Start with a GitHub repository."
      />
      <div className="grid gap-6 xl:grid-cols-5">
        <Panel className="xl:col-span-3">
          <div className="border-b p-6">
            <div className="mb-4 flex size-11 items-center justify-center rounded-lg border bg-canvas">
              <Github className="size-6" />
            </div>
            <Heading level={2}>Connect with a repository URL</Heading>
            <p className="mt-2 text-sm text-muted-foreground">
              Validate your repository before adding it to your workspace.
            </p>
          </div>
          <div className="space-y-5 p-6">
            <form
              onSubmit={(event) => {
                event.preventDefault()
                validate()
              }}
            >
              <label
                htmlFor="repo-url"
                className="mb-2 block text-xs font-medium"
              >
                GitHub repository URL
              </label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  id="repo-url"
                  value={url}
                  onChange={(event) => {
                    setUrl(event.target.value)
                    setState("idle")
                  }}
                  placeholder="https://github.com/organization/repository"
                  aria-invalid={!!validationMessages[state]}
                  aria-describedby={
                    validationMessages[state] ? "validation-error" : "repo-hint"
                  }
                  className="h-10 bg-background"
                  required
                />
                <Button
                  type="submit"
                  disabled={state === "loading"}
                  className="h-10 shrink-0 px-4"
                >
                  {state === "loading" ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Validating…
                    </>
                  ) : (
                    <>
                      Validate repository
                      <ArrowRight className="size-4" />
                    </>
                  )}
                </Button>
              </div>
              <p id="repo-hint" className="mt-2 text-xs text-muted-foreground">
                For the demo, try https://github.com/Amalitech/payment-service.
              </p>
            </form>
            {validationMessages[state] && (
              <div id="validation-error">
                <Notice
                  tone="error"
                  title={validationMessages[state][0]}
                  action={
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={validate}>
                        Retry validation
                      </Button>
                      <Button variant="ghost" onClick={() => setState("idle")}>
                        Go back
                      </Button>
                    </div>
                  }
                >
                  {validationMessages[state][1]}
                </Notice>
              </div>
            )}
            {state === "loading" && (
              <div role="status" className="space-y-3 rounded-lg border p-5">
                <p className="text-sm font-medium">Validating repository…</p>
                {[
                  "Checking repository URL",
                  "Confirming demo access",
                  "Checking supported project",
                ].map((text, index) => (
                  <p
                    key={text}
                    className="flex items-center gap-2 text-xs text-muted-foreground"
                  >
                    {index === 0 ? (
                      <Check className="size-3.5 text-trust" />
                    ) : (
                      <Loader2 className="size-3.5 animate-spin" />
                    )}
                    {text}
                  </p>
                ))}
              </div>
            )}
            {state === "success" && preview && (
              <div className="space-y-4">
                <Notice title="Repository validated" tone="success">
                  Repository exists in the demo · Access confirmed in sample
                  data · Supported project · Ready to scan
                </Notice>
                <div className="rounded-lg border p-5">
                  <RepoIdentity repo={preview} subtitle />
                  <p className="mt-3 break-all font-mono text-xs text-muted-foreground">
                    {preview.url || `https://github.com/${preview.name}`}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Owner: {preview.owner || preview.name.split("/")[0]}
                  </p>
                  <div className="mt-5 grid grid-cols-2 gap-y-4 text-xs">
                    <div>
                      <p className="text-muted-foreground">Visibility</p>
                      <p className="mt-1.5">{preview.visibility}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Default branch</p>
                      <p className="mt-1.5 font-mono">{preview.branch}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Primary language</p>
                      <p className="mt-1.5">{preview.language}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Latest commit</p>
                      <p className="mt-1.5 font-mono">
                        {preview.commit} · demo
                      </p>
                    </div>
                  </div>
                </div>
                <label className="flex items-start gap-3 text-xs leading-relaxed">
                  <Checkbox
                    checked={permissionConfirmed}
                    onCheckedChange={(checked) =>
                      setPermissionConfirmed(checked === true)
                    }
                    aria-label="Confirm repository permission"
                  />
                  I have permission to submit and analyze this repository.
                  Access validation is simulated in this frontend preview.
                </label>
                <Button
                  disabled={!permissionConfirmed}
                  className="h-10 w-full"
                  onClick={() => {
                    const exists = store.repositories.some(
                      (repo) => repo.id === preview.id,
                    )
                    if (!exists) store.addRepository(preview)
                    toast.success(
                      exists
                        ? "Repository already connected"
                        : "Repository connected",
                      { description: preview.name },
                    )
                    navigate(`/repositories/${preview.id}`)
                  }}
                >
                  {store.repositories.some((repo) => repo.id === preview.id)
                    ? "Open repository"
                    : "Add repository"}
                  <ArrowRight className="size-4" />
                </Button>
              </div>
            )}
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex-1 border-t" />
              or
              <span className="flex-1 border-t" />
            </div>
            <Button
              variant="outline"
              className="h-10 w-full"
              onClick={() => setGithub(true)}
            >
              <Github className="size-4" />
              Connect GitHub
            </Button>
          </div>
          <div className="border-t bg-canvas px-6 py-4 text-xs leading-relaxed text-muted-foreground">
            This is a frontend prototype. URL validation and repository
            permissions are simulated; no GitHub account or repository content
            is accessed.
          </div>
        </Panel>
        <div className="space-y-5 xl:col-span-2">
          <Panel>
            <PanelHeader title="Before you connect" />
            <div className="space-y-5 px-5 pb-5">
              {[
                {
                  title: "A GitHub repository",
                  copy: "Public or private, with permission to analyze the code.",
                },
                {
                  title: "A supported project",
                  copy: "Python, JavaScript, TypeScript, or Terraform. Coverage varies by scanner.",
                },
                {
                  title: "Read-only access",
                  copy: "Analysis does not modify your code or create pull requests.",
                },
              ].map((item) => (
                <div key={item.title} className="flex gap-3">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-trust" />
                  <div>
                    <p className="text-xs font-medium">{item.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                      {item.copy}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
          <Notice title="Isolated by design">
            Repository content is treated as untrusted input and analyzed within
            an isolated scan environment.
          </Notice>
          <details className="rounded-lg border bg-background p-4 text-xs">
            <summary className="cursor-pointer text-muted-foreground">
              Preview validation states
            </summary>
            <p className="my-3 text-muted-foreground">
              Choose a sample response, then validate a GitHub URL.
            </p>
            <div className="flex flex-wrap gap-2">
              {["success", "missing", "denied", "unsupported", "offline"].map(
                (item) => (
                  <Button
                    key={item}
                    variant={scenario === item ? "default" : "outline"}
                    className="h-7 text-xs"
                    onClick={() => {
                      setScenario(item)
                      setState("idle")
                    }}
                  >
                    {item}
                  </Button>
                ),
              )}
            </div>
          </details>
        </div>
      </div>
      <Dialog open={github} onOpenChange={setGithub}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>GitHub connection preview</DialogTitle>
            <DialogDescription>
              OAuth is not connected in this frontend prototype. Choose a sample
              repository or connect one by URL.
            </DialogDescription>
          </DialogHeader>
          {["Amalitech/payment-service", "Amalitech/design-system"].map(
            (name) => (
              <Button
                key={name}
                variant="outline"
                className="h-10 justify-start"
                onClick={() => {
                  setUrl(`https://github.com/${name}`)
                  setGithub(false)
                  setState("idle")
                }}
              >
                <Github className="size-4" />
                {name}
                <Plus className="ml-auto size-3" />
              </Button>
            ),
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}

export function RepositoryDetail({ start = false }: { start?: boolean }) {
  const { id } = useParams()
  const store = useStore()
  const navigate = useNavigate()
  const [scanOpen, setScanOpen] = useState(start)
  const [params] = useSearchParams()
  const [tab, setTab] = useState(params.get("tab") || "overview")
  const repo = store.repositories.find((item) => item.id === id)
  if (store.isRestricted(id)) return <AccessDenied />
  if (!repo)
    return (
      <EmptyState
        title="Repository not found"
        description="This repository is not connected to your workspace."
        action={<LinkButton to="/repositories">View repositories</LinkButton>}
      />
    )
  const repoScans = store.scans.filter((scan) => scan.repoId === id)
  const latest = repoScans[0]
  const report = repoScans.find((scan) =>
    ["Completed", "Partial"].includes(scan.status),
  )
  const findings = getRepositoryFindings(repo.id, store.scans, store.findings)
  const open = findings.filter(
    (findingRecord) => findingRecord.status === "Open",
  )
  return (
    <PageState kind="Repository details">
      <Breadcrumbs
        items={[
          { label: "Repositories", to: "/repositories" },
          { label: repo.name },
        ]}
      />
      <PageHeader
        title={repo.name}
        description={repo.description}
        eyebrow="REPOSITORY"
      >
        <Button
          variant="outline"
          className="h-9"
          disabled={!report}
          onClick={() => report && navigate(`/reports/${report.id}`)}
        >
          View report
        </Button>
        <Button className="h-9" onClick={() => setScanOpen(true)}>
          <Play className="size-3.5" />
          Start scan
        </Button>
      </PageHeader>
      <div className="mb-6 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <LockKeyhole className="size-3.5" />
          {repo.visibility}
        </span>
        <span className="flex items-center gap-1.5">
          <GitBranch className="size-3.5" />
          <span className="font-mono">{repo.branch}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <Code2 className="size-3.5" />
          {repo.language}
        </span>
        <span className="flex items-center gap-1.5">
          <GitCommitHorizontal className="size-3.5" />
          <span className="font-mono">{repo.commit}</span>
        </span>
        <span>Owner: {repo.owner || repo.name.split("/")[0]}</span>
        <span>Connected {repo.connected}</span>
        <a
          href={repo.url || `https://github.com/${repo.name}`}
          target="_blank"
          rel="noreferrer"
          className="break-all font-mono hover:underline"
        >
          {repo.url || `https://github.com/${repo.name}`}
        </a>
      </div>
      <Tabs value={tab} onValueChange={(value) => setTab(String(value))}>
        <TabsList
          variant="line"
          className="mb-5 h-10 w-full justify-start gap-6 border-b px-0"
        >
          {["overview", "scans", "findings", "reports"].map((item) => (
            <TabsTrigger
              key={item}
              value={item}
              className="h-9 flex-none px-0 text-xs capitalize"
            >
              {item}
              {item === "findings" && (
                <Badge variant="secondary" className="ml-1 rounded-md">
                  {findings.length}
                </Badge>
              )}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="overview">
          <div className="grid gap-5 xl:grid-cols-3">
            <Panel className="xl:col-span-2">
              <PanelHeader
                title="Security posture"
                action={
                  <Badge
                    variant="secondary"
                    className={cn(
                      "rounded-md",
                      open.length
                        ? "bg-medium-soft text-medium"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    {latest
                      ? open.length
                        ? "Needs attention"
                        : "No open findings"
                      : "Not scanned"}
                  </Badge>
                }
              />
              <div className="px-5 pb-5">
                <p className="mb-5 text-sm text-muted-foreground">
                  {findings.length
                    ? `${open.length} open findings in the latest available scanner evidence.`
                    : "Run a scan to gather evidence about this repository."}
                </p>
                <SeverityDistribution findings={open} />
              </div>
            </Panel>
            <Panel>
              <PanelHeader title="Latest scan" />
              <div className="px-5 pb-5">
                {latest ? (
                  <>
                    <div className="flex items-center justify-between">
                      <p className="text-2xl font-semibold">#{latest.id}</p>
                      <StatusBadge status={latest.status} />
                    </div>
                    <p className="mt-4 text-xs text-muted-foreground">
                      {latest.date}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Duration: {latest.duration}
                    </p>
                    <LinkButton
                      to={`/scans/${latest.id}`}
                      className="mt-5 w-full"
                    >
                      View scan
                      <ArrowRight className="size-3" />
                    </LinkButton>
                  </>
                ) : (
                  <EmptyState
                    title="No scans yet"
                    description="Start your first scan to collect security evidence."
                    action={
                      <Button onClick={() => setScanOpen(true)}>
                        Start scan
                      </Button>
                    }
                  />
                )}
              </div>
            </Panel>
          </div>
          <Panel className="mt-5">
            <PanelHeader
              title="Analysis coverage"
              description="Independent tools provide evidence across four security categories."
            />
            <div className="grid divide-y sm:grid-cols-2 sm:divide-y-0 xl:grid-cols-4">
              {scannerInfo.map((scanner) => (
                <div key={scanner.name} className="border-t px-5 py-5">
                  <p className="text-sm font-semibold">{scanner.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {scanner.description}
                  </p>
                  <div className="mt-5 flex items-center justify-between">
                    <span className="text-xs">
                      {
                        findings.filter(
                          (findingRecord) =>
                            findingRecord.scanner === scanner.name,
                        ).length
                      }{" "}
                      findings
                    </span>
                    <StatusBadge
                      status={
                        latest?.status === "Partial" &&
                        scanner.name === "Checkov"
                          ? "Failed"
                          : report
                            ? "Completed"
                            : "Not scanned"
                      }
                    />
                  </div>
                </div>
              ))}
            </div>
          </Panel>
          <div className="mt-5">
            <Notice>
              Scanners collect security evidence. AI interprets that evidence
              and repository context. Neither establishes complete security or
              guaranteed exploitability.
            </Notice>
          </div>
        </TabsContent>
        <TabsContent value="scans">
          {repoScans.length ? (
            <Panel>
              <Table className="hidden sm:table">
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-5">Scan</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {repoScans.map((scan) => (
                    <TableRow key={scan.id}>
                      <TableCell className="py-4 pl-5 font-mono text-xs">
                        #{scan.id}
                      </TableCell>
                      <TableCell className="text-xs">{scan.date}</TableCell>
                      <TableCell>
                        <StatusBadge status={scan.status} />
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {scan.duration}
                      </TableCell>
                      <TableCell>
                        <LinkButton to={`/scans/${scan.id}`} variant="ghost">
                          View
                          <ArrowRight className="size-3" />
                        </LinkButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="sm:hidden">
                {repoScans.map((scan) => (
                  <Link
                    key={scan.id}
                    to={`/scans/${scan.id}`}
                    className="block border-b p-4 last:border-0"
                  >
                    <div className="flex justify-between">
                      <span className="font-mono text-xs">Scan #{scan.id}</span>
                      <StatusBadge status={scan.status} />
                    </div>
                    <p className="mt-3 text-xs text-muted-foreground">
                      {scan.date} · {scan.duration}
                    </p>
                  </Link>
                ))}
              </div>
            </Panel>
          ) : (
            <Panel>
              <EmptyState
                title="No scans have been run for this repository"
                description="Run a security scan to build an evidence-backed history."
                action={
                  <Button onClick={() => setScanOpen(true)}>Start scan</Button>
                }
              />
            </Panel>
          )}
        </TabsContent>
        <TabsContent value="findings">
          {findings.length ? (
            <Panel>
              {findings.map((finding) => (
                <Link
                  key={finding.id}
                  to={`/scans/${finding.scanId || report?.id || latest?.id}/findings/${finding.id}`}
                  className="flex flex-wrap items-center gap-4 border-b px-5 py-4 last:border-0 hover:bg-muted/40"
                >
                  <SeverityBadge severity={finding.severity} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{finding.title}</p>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {finding.file}:{finding.line}
                    </p>
                  </div>
                  <Confidence value={finding.confidence} />
                  <ChevronRight className="size-4 text-muted-foreground" />
                </Link>
              ))}
            </Panel>
          ) : (
            <Panel>
              <EmptyState
                icon={ShieldCheck}
                title="No findings available"
                description={
                  latest
                    ? "No findings were detected in the configured checks. This does not establish complete security."
                    : "Run a scan to collect security evidence."
                }
                action={
                  <Button onClick={() => setScanOpen(true)}>Start scan</Button>
                }
              />
            </Panel>
          )}
        </TabsContent>
        <TabsContent value="reports">
          {repoScans.filter((scan) =>
            ["Completed", "Partial"].includes(scan.status),
          ).length ? (
            <Panel>
              {repoScans
                .filter((scan) =>
                  ["Completed", "Partial"].includes(scan.status),
                )
                .map((scan) => (
                  <div
                    key={scan.id}
                    className="flex flex-wrap items-center justify-between gap-4 border-b p-5 last:border-0"
                  >
                    <div>
                      <p className="text-sm font-medium">
                        Security report · Scan #{scan.id}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {scan.date} ·{" "}
                        {getScanFindings(scan, store.findings).length} findings
                      </p>
                    </div>
                    <LinkButton to={`/reports/${scan.id}`}>
                      View report
                      <ArrowRight className="size-3" />
                    </LinkButton>
                  </div>
                ))}
            </Panel>
          ) : (
            <Panel>
              <EmptyState
                title="No security reports yet"
                description="A report will be available after your first completed scan."
              />
            </Panel>
          )}
        </TabsContent>
      </Tabs>
      <ScanDialog repo={repo} open={scanOpen} onOpenChange={setScanOpen} />
    </PageState>
  )
}
