"use client"

import { useEffect, useState, type ReactNode, type ComponentType } from "react"
import { Link, useNavigate, useSearchParams } from "@/lib/router"
import {
  ArrowRight,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  Circle,
  CircleAlert,
  Code2,
  Copy,
  Download,
  FileCode2,
  FolderGit2,
  GitBranch,
  Github,
  Info,
  KeyRound,
  Layers3,
  Loader2,
  LockKeyhole,
  Play,
  Plus,
  Search,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react"
import { toast } from "sonner"
import { Button, buttonVariants } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select } from "@base-ui/react/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import {
  categories,
  type DemoOutcome,
  severityOrder,
  type Category,
  type Finding,
  type Repository,
  type Severity,
} from "@/lib/security-model"
import { useRepositories, useTriggerScan, useGitHubStatus, useRepositoryBranches, useScans, useFindings, useCancelScan } from "@/lib/api/hooks"
import { useDownloadReportPdf, useGenerateReport, useReport } from "@/lib/api/hooks"
import { getScanOutcome, scanOutcomeLabels } from "@/lib/scan-status"

export const severityStyles: Record<Severity, string> = {
  Critical: "bg-critical-soft text-critical",
  High: "bg-high-soft text-high",
  Medium: "bg-medium-soft text-medium",
  Low: "bg-low-soft text-low",
}
export const severityColors: Record<Severity, string> = {
  Critical: "bg-critical",
  High: "bg-high",
  Medium: "bg-medium",
  Low: "bg-low",
}
export const categoryIcons: Record<Category, ComponentType<{
  className?: string
}>> = {
  Code: Code2,
  Secrets: KeyRound,
  Dependencies: Layers3,
  Configuration: FileCode2,
}
export function Heading({
  children,
  level = 1,
  className,
}: {
  children: ReactNode
  level?: number
  className?: string
}) {
  return (
    <p
      role="heading"
      aria-level={level}
      className={cn(
        level === 1
          ? "text-3xl font-semibold tracking-normal"
          : "text-base font-semibold",
        className,
      )}
    >
      {children}
    </p>
  )
}
export function LinkButton({
  to,
  children,
  variant = "outline",
  className,
}: {
  to: string
  children: ReactNode
  variant?: "outline" | "default" | "ghost"
  className?: string
}) {
  return (
    <Link
      to={to}
      data-slot="button"
      className={cn(buttonVariants({ variant }), "h-9 gap-2 px-3.5", className)}
    >
      {children}
    </Link>
  )
}
export function Panel({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <Card
      className={cn(
        "gap-0 rounded-lg border bg-card p-0 shadow-none ring-0",
        className,
      )}
    >
      {children}
    </Card>
  )
}
export function PanelHeader({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-5 py-4">
      <div>
        <Heading level={2} className="text-sm">
          {title}
        </Heading>
        {description && (
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}
export function PageHeader({
  title,
  description,
  eyebrow,
  children,
}: {
  title: string
  description?: string
  eyebrow?: string
  children?: ReactNode
}) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-5">
      {" "}
      <div>
        {eyebrow && (
          <p className="mb-2 text-xs font-medium tracking-widest text-muted-foreground">
            {eyebrow}
          </p>
        )}
        <Heading>{title}</Heading>
        {description && (
          <p className="mt-2 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {children && (
        <div className="flex flex-wrap items-center gap-2.5">{children}</div>
      )}
    </div>
  )
}
export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge
      variant="secondary"
      className={cn(
        "h-6 gap-1.5 rounded-md px-2 font-medium",
        severityStyles[severity],
      )}
    >
      <span className={cn("size-1.5 rounded-full", severityColors[severity])} />
      {severity}
    </Badge>
  )
}
export function StatusBadge({ status }: { status: string }) {
  const scanStatuses = ["Completed", "Partial", "Failed", "Running", "Queued", "Cancelled"]
  const displayStatus = scanStatuses.includes(status) ? scanOutcomeLabels[getScanOutcome({ status })] : status
  const success = ["Completed", "Reviewed", "Resolved", "Connected"].includes(
    status,
  )
  const warning = ["Partial", "Queued"].includes(status)
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap text-xs",
        success
          ? "text-trust"
          : warning
            ? "text-medium"
          : status === "Failed"
              ? "text-critical"
              : "text-muted-foreground",
      )}
    >
      {success ? (
        <CheckCheck className="size-3.5" />
      ) : status === "Running" ? (
        <Loader2 className="size-3.5 animate-spin motion-reduce:animate-none" />
      ) : warning || status === "Failed" ? (
        <CircleAlert className="size-3.5" />
      ) : (
        <Circle className="size-3" />
      )}
      {displayStatus}
    </span>
  )
}
export function Confidence({ value }: { value: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className="flex items-end gap-0.5" aria-hidden="true">
        <span className="h-1.5 w-0.5 rounded-full bg-muted-foreground" />
        <span
          className={cn(
            "h-2.5 w-0.5 rounded-full",
            value === "Low" ? "bg-muted" : "bg-muted-foreground",
          )}
        />
        <span
          className={cn(
            "h-3.5 w-0.5 rounded-full",
            value === "High" ? "bg-muted-foreground" : "bg-muted",
          )}
        />
      </span>
      {value} confidence
    </span>
  )
}
export function SearchInput({
  value,
  onChange,
  placeholder,
  className,
}: {
  value: string
  onChange: (value: string) => void
  placeholder: string
  className?: string
}) {
  return (
    <div className={cn("relative", className)}>
      <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        aria-label={placeholder}
        type="search"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 bg-background pl-9"
      />
    </div>
  )
}
export function SelectControl({
  value,
  onChange,
  options,
  label,
}: {
  value: string
  onChange: (value: string) => void
  options: string[]
  label: string
}) {
  return (
    <Select.Root
      value={value}
      onValueChange={(nextValue) => {
        if (nextValue !== null) onChange(nextValue)
      }}
      items={options.map((option) => ({ label: option, value: option }))}
    >
      <Select.Trigger
        aria-label={label}
        className="group inline-flex h-9 items-center justify-between gap-3 rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition-colors hover:bg-muted focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 data-[popup-open]:border-ring data-[popup-open]:bg-muted"
      >
        <Select.Value />
        <Select.Icon>
          <ChevronDown className="size-3.5 text-muted-foreground transition-transform group-data-[popup-open]:rotate-180" />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Positioner
          align="start"
          sideOffset={6}
          alignItemWithTrigger={false}
          className="z-50 outline-none"
        >
          <Select.Popup className="min-w-(--anchor-width) origin-(--transform-origin) rounded-lg border border-border bg-popover p-1.5 text-popover-foreground shadow-lg transition-[opacity,transform] duration-150 data-[ending-style]:scale-95 data-[ending-style]:opacity-0 data-[starting-style]:scale-95 data-[starting-style]:opacity-0 motion-reduce:transition-none">
            <Select.List className="max-h-(--available-height) overflow-y-auto scroll-py-1 outline-none">
              {options.map((option) => (
                <Select.Item
                  key={option}
                  value={option}
                  className="flex min-h-9 cursor-pointer items-center justify-between gap-5 rounded-md px-2.5 py-2 text-sm outline-none transition-colors data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground data-[selected]:bg-trust-soft data-[selected]:font-medium data-[selected]:text-trust"
                >
                  <Select.ItemText>{option}</Select.ItemText>
                  <span className="flex size-4 shrink-0 items-center justify-center">
                    <Select.ItemIndicator>
                      <Check className="size-3.5" />
                    </Select.ItemIndicator>
                  </span>
                </Select.Item>
              ))}
            </Select.List>
          </Select.Popup>
        </Select.Positioner>
      </Select.Portal>
    </Select.Root>
  )
}

export function BranchSelect({ repoId, value, onChange }: { repoId: string; value: string; onChange: (value: string) => void }) {
  const { data, isLoading, isError, refetch } = useRepositoryBranches(repoId)
  const branches = data ?? []
  return (
    <div className="space-y-2">
      <label htmlFor="scan-branch" className="text-xs font-medium">Branch</label>
      <Input id="scan-branch" list="repository-branches" value={value} disabled={isLoading || isError || branches.length <= 1} onChange={(event) => onChange(event.target.value)} placeholder={isLoading ? "Loading branches…" : "Search branches"} aria-describedby="branch-help" />
      <datalist id="repository-branches">{branches.map((branch) => <option key={branch.name} value={branch.name}>{branch.is_default ? "Default" : ""}</option>)}</datalist>
      <p id="branch-help" className="text-xs text-muted-foreground">{isLoading ? "Loading available branches…" : isError ? <><span>Branches could not be loaded. </span><button type="button" className="underline" onClick={() => refetch()}>Retry</button></> : branches.length <= 1 ? "This repository has only one branch." : "Search and select the branch to scan."}</p>
    </div>
  )
}
export function Notice({
  title,
  children,
  tone = "neutral",
  action,
}: {
  title?: string
  children: ReactNode
  tone?: "neutral" | "warning" | "error" | "success"
  action?: ReactNode
}) {
  const Icon =
    tone === "warning" || tone === "error"
      ? TriangleAlert
      : tone === "success"
        ? ShieldCheck
        : Info
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "flex items-start gap-3 rounded-lg border p-4 text-sm",
        tone === "warning"
          ? "border-medium/20 bg-medium-soft text-medium"
          : tone === "error"
            ? "border-critical/20 bg-critical-soft text-critical"
            : tone === "success"
              ? "border-trust/20 bg-trust-soft text-trust"
              : "border-border bg-muted/35 text-muted-foreground",
      )}
    >
      <Icon className="mt-0.5 size-4 shrink-0" />
      <div className="min-w-0 flex-1">
        {title && <p className="mb-1 font-medium">{title}</p>}
        <div className="text-xs leading-relaxed">{children}</div>
        {action && <div className="mt-3">{action}</div>}
      </div>
    </div>
  )
}
export function EmptyState({
  title,
  description,
  action,
  icon: Icon = FolderGit2,
}: {
  title: string
  description: string
  action?: ReactNode
  icon?: ComponentType<{ className?: string }>
}) {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-4 flex size-12 items-center justify-center rounded-xl border bg-muted/40">
        <Icon className="size-5 text-muted-foreground" />
      </div>
      <Heading level={2}>{title}</Heading>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
export function AccessDenied() {
  return (
    <EmptyState
      icon={LockKeyhole}
      title="You don't have permission to view this repository."
      description="Request access from your workspace administrator. No repository details are displayed."
      action={<LinkButton to="/dashboard">Back to dashboard</LinkButton>}
    />
  )
}
export function PageState({
  children,
  kind,
}: {
  children: ReactNode
  kind: string
}) {
  const [params, setParams] = useSearchParams()
  const state = params.get("state")
  if (state === "loading")
    return (
      <div role="status" aria-label={`Loading ${kind}`} className="space-y-6">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-4 w-96 max-w-full" />
        <div className="grid gap-5 sm:grid-cols-3">
          {[1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-96" />
        <Button variant="outline" onClick={() => setParams({})}>
          Finish loading preview
        </Button>
      </div>
    )
  if (state === "unauthorized")
    return (
      <EmptyState
        icon={LockKeyhole}
        title="You don't have permission to view this repository."
        description="Request access from your workspace administrator. No repository details are displayed."
        action={<LinkButton to="/dashboard">Back to dashboard</LinkButton>}
      />
    )
  if (state === "error")
    return (
      <div className="space-y-6">
        <Notice
          title={`We couldn't load ${kind.toLowerCase()}.`}
          tone="error"
          action={
            <Button variant="outline" onClick={() => setParams({})}>
              Try again
            </Button>
          }
        >
          A network connection failed. Saved scanner evidence remains available
          in your workspace.
        </Notice>
        <LinkButton to="/dashboard">Back to dashboard</LinkButton>
      </div>
    )
  if (state === "empty")
    return (
      <Panel>
        <EmptyState
          title={`No ${kind.toLowerCase()} yet`}
          description="Connect a GitHub repository and run a security scan to get started."
          action={
            <LinkButton to="/repositories/new" variant="default">
              <Plus className="size-4" />
              Connect repository
            </LinkButton>
          }
        />
      </Panel>
    )
  return <>{children}</>
}
export function SeverityDistribution({
  findings,
  compact = false,
}: {
  findings: Finding[]
  compact?: boolean
}) {
  return (
    <div>
      <div
        className={cn(
          "flex overflow-hidden rounded-sm bg-muted",
          compact ? "h-2" : "h-3",
        )}
      >
        {severityOrder.map((severity) => {
          const count = findings.filter(
            (finding) => finding.severity === severity,
          ).length
          return count ? (
            <div
              key={severity}
              title={`${count} ${severity.toLowerCase()} findings`}
              className={cn(
                "border-r-2 border-background last:border-0",
                severityColors[severity],
              )}
              style={{ flexGrow: count }}
            />
          ) : null
        })}
      </div>
      <div className={cn("mt-5 grid grid-cols-4 gap-3", compact && "mt-3")}>
        {severityOrder.map((severity) => (
          <div key={severity}>
            <p
              className={cn(
                "font-semibold tabular-nums",
                compact ? "text-base" : "text-2xl",
              )}
            >
              {
                findings.filter((finding) => finding.severity === severity)
                  .length
              }
            </p>
            <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  severityColors[severity],
                )}
              />
              {severity}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
export function CodeBlock({
  code,
  filename,
  highlight = true,
  highlightLine,
}: {
  code: string
  filename?: string
  highlight?: boolean
  highlightLine?: number
}) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="overflow-hidden rounded-lg border bg-canvas">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <span className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
          <FileCode2 className="size-3.5" />
          {filename || "Code example"}
        </span>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Copy code"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(code)
              setCopied(true)
              setTimeout(() => setCopied(false), 1500)
            } catch {
              toast.error("Clipboard unavailable", {
                description: "Select and copy the code manually.",
              })
            }
          }}
        >
          {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
        </Button>
      </div>
      <pre className="overflow-x-auto py-4 font-mono text-xs leading-7">
        {code.split("\n").map((line, index) => (
          <div
            key={index}
            className={cn(
              "min-w-max px-4",
              highlight &&
                (highlightLine
                  ? Number(line.match(/^\s*(\d+)\s/)?.[1]) === highlightLine
                  : index === 2) &&
                "border-l-2 border-high bg-high-soft",
            )}
          >
            <code>{line || " "}</code>
          </div>
        ))}
      </pre>
    </div>
  )
}
export function RepoIdentity({
  repo,
  subtitle,
}: {
  repo: Repository
  subtitle?: boolean
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-canvas">
        <Github className="size-4" />
      </span>
      <div className="min-w-0">
        <Link
          to={`/repositories/${repo.id}`}
          className="text-sm font-medium hover:underline"
        >
          {repo.name}
        </Link>
        {subtitle && (
          <p className="mt-1 text-xs text-muted-foreground">
            {repo.description}
          </p>
        )}
      </div>
    </div>
  )
}
export function RepositoryCard({ repo }: { repo: Repository }) {
  const { data: scansData } = useScans(1, 100, repo.id)
  const { data: findingsData } = useFindings({ repo_id: repo.id, page_size: 1000 })
  const scans = scansData?.items || []
  const findings = findingsData?.items || []
  const latest = scans.find((scan) => ["Completed", "Partial"].includes(scan.status))
  const list = findings.filter(
    (findingRecord) =>
      findingRecord.status !== "Resolved" &&
      findingRecord.status !== "False positive",
  )
  const highest = severityOrder.find((severity) =>
    list.some((finding) => finding.severity === severity),
  )
  return (
    <Panel>
      <div className="p-4">
        <div className="flex items-center justify-between">
          <Github className="size-5" />
          <Badge variant="outline" className="rounded-md text-muted-foreground">
            {repo.visibility}
          </Badge>
        </div>
        <Link
          to={`/repositories/${repo.id}`}
          className="mt-4 block text-sm font-semibold hover:underline"
        >
          {repo.name}
        </Link>
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {repo.description}
        </p>
        <div className="mt-4 flex gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span
              className={cn(
                "size-2 rounded-full",
                repo.language === "Python" ? "bg-medium" : "bg-low",
              )}
            />
            {repo.language}
          </span>
          <span className="flex items-center gap-1">
            <GitBranch className="size-3" />
            {repo.branch}
          </span>
        </div>
      </div>
      <div className="flex items-center justify-between border-t px-4 py-3">
        <span className="text-xs text-muted-foreground">
          {list.length} findings{" "}
          {highest && (
            <span
              className={cn(
                "ml-1.5",
                highest === "Critical" || highest === "High"
                  ? "text-high"
                  : "text-muted-foreground",
              )}
            >
              · {highest}
            </span>
          )}
        </span>
        <Link
          to={`/repositories/${repo.id}`}
          aria-label={`View ${repo.name}`}
          className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <ArrowRight className="size-4" />
        </Link>
      </div>
      {latest && latest.status === "Failed" && (
        <div className="px-4 pb-3">
          <StatusBadge status="Failed" />
        </div>
      )}
    </Panel>
  )
}

export function ScanDialog({
  repo,
  initialBranch,
  open,
  onOpenChange,
}: {
  repo?: Repository
  initialBranch?: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const navigate = useNavigate()
  const { data: reposData } = useRepositories(1, 100)
  const repositories = reposData?.items || []
  const { data: isGitHubConnected } = useGitHubStatus()
  const { mutateAsync: triggerScan } = useTriggerScan()
  
  const [selected, setSelected] = useState(
    repo?.id || repositories[0]?.id || "",
  )
  const activeRepo = repo || repositories.find((item) => item.id === selected)
  const { data: branches } = useRepositoryBranches(activeRepo?.id || "")
  const [branch, setBranch] = useState(initialBranch || "")
  const defaultBranch = branches?.find((item) => item.is_default)?.name || activeRepo?.branch || ""
  useEffect(() => { if (defaultBranch && (!branch || !branches?.some((item) => item.name === branch))) setBranch(initialBranch || defaultBranch) }, [defaultBranch, initialBranch, branch, branches])
  const [params] = useSearchParams()
  const [error, setError] = useState(false)
  const [githubError, setGithubError] = useState(false)
  const [launching, setLaunching] = useState(false)
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <div className="mb-2 flex size-10 items-center justify-center rounded-lg border bg-trust-soft">
            <ShieldCheck className="size-5 text-trust" />
          </div>
          <DialogTitle className="text-lg">Start security scan</DialogTitle>
          <DialogDescription>
            Four independent security checks. One evidence-backed report.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-5 py-3">
          <div>
            <p className="mb-2 text-xs font-medium">Repository</p>
            {repo ? (
              <div className="rounded-lg border p-3">
                <RepoIdentity repo={repo} />
              </div>
            ) : (
              <SelectControl
                label="Repository to scan"
                value={selected}
                onChange={setSelected}
                options={repositories.map((item) => item.id)}
              />
            )}
          </div>
          <BranchSelect repoId={activeRepo?.id || ""} value={branch || defaultBranch} onChange={setBranch} />
          <div className="grid grid-cols-2 gap-3">
            {categories.map((category) => {
              const Icon = categoryIcons[category]
              return (
                <div
                  key={category}
                  className="flex items-center gap-2 rounded-lg border p-3 text-xs"
                >
                  <Icon className="size-4 text-muted-foreground" />
                  {category}
                  <Check className="ml-auto size-3 text-trust" />
                </div>
              )
            })}
          </div>
          <Notice>
            All four checks are enabled. Repository content is analyzed in an
            isolated environment. Analysis may take several minutes depending on
            repository size.
          </Notice>
          <p className="text-xs text-muted-foreground">
            Frontend demo: progress is simulated. No repository is cloned or
            scanned.
          </p>
          {error && (
            <Notice title="Scan could not be created" tone="error">
              The scan queue could not be reached. Previous scan results are
              still available. Retry after restoring the connection.
            </Notice>
          )}
          {githubError && (
            <Notice
              tone="error"
              title="GitHub is disconnected"
              action={
                <LinkButton to="/settings?tab=github">
                  Restore connection
                </LinkButton>
              }
            >
              Your saved findings remain available. Restore the demo connection
              in Settings before starting a new scan.
            </Notice>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={launching || (!repo && !selected)}
            onClick={async () => {
              if (isGitHubConnected?.connected === false) {
                setGithubError(true)
                return
              }
              setGithubError(false)
              if (params.get("state") === "scan-error" && !error) {
                setError(true)
                return
              }
              setLaunching(true)
              try {
                const branchToScan = branch || defaultBranch;
                if (!branchToScan) throw new Error("Select a branch before starting the scan.")
                const scan = await triggerScan({ repo_id: repo?.id || selected, branch: branchToScan })
                onOpenChange(false)
                setLaunching(false)
                navigate(`/scans/${scan.id}`)
                toast.success("Security scan queued", {
                  description: "Scan started.",
                })
              } catch (failure) {
                toast.error(
                  failure instanceof Error
                    ? failure.message
                    : "Could not create the scan. Existing results remain available.",
                )
                setLaunching(false)
              }
            }}
          >
            {launching ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Play className="size-3.5" />
            )}
            Start scan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
export function DownloadReport({
  scanId,
  variant = "outline",
}: {
  scanId: string
  variant?: "default" | "outline" | "ghost"
}) {
  const { mutateAsync: generate } = useGenerateReport()
  const { mutateAsync: downloadPdf, isPending } = useDownloadReportPdf()
  const { data: existing } = useReport(scanId)
  async function download() { try { const report = existing?.status === "ready" ? existing : await generate({ scan_id: scanId }); const blob = await downloadPdf(report.id); const url = URL.createObjectURL(blob); const element = document.createElement("a"); element.href = url; element.download = report.file_name; element.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); toast.success("PDF report downloaded") } catch (error) { toast.error(error instanceof Error ? error.message : "Could not download the PDF.") } }
  return (
    <>
      <Button
        variant={variant}
        className="h-9 gap-2"
        onClick={download}
        disabled={isPending}
      >
        {isPending ? <Loader2 className="size-3.5 animate-spin" /> : <Download className="size-3.5" />}
        Download PDF
      </Button>
    </>
  )
}

export function CancelScanDialog({ scanId, open, onOpenChange }: { scanId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const { mutateAsync: cancel, isPending } = useCancelScan()
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent><DialogHeader><DialogTitle>Cancel this scan?</DialogTitle><DialogDescription>Results found so far will not be saved.</DialogDescription></DialogHeader><DialogFooter><Button variant="outline" disabled={isPending} onClick={() => onOpenChange(false)}>Keep scanning</Button><Button variant="destructive" disabled={isPending} onClick={async () => { try { await cancel(scanId); toast.success("Scan cancelled") ; onOpenChange(false) } catch (error) { toast.error(error instanceof Error ? error.message : "Could not cancel scan.") } }}>{isPending ? "Cancelling…" : "Cancel scan"}</Button></DialogFooter></DialogContent></Dialog>
}

export function ReportPreview({ reportId, enabled }: { reportId: string; enabled: boolean }) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { mutateAsync: download, isPending } = useDownloadReportPdf()
  useEffect(() => {
    if (!enabled) return
    let active = true
    download(reportId).then((blob) => { if (active) setUrl(URL.createObjectURL(blob)) }).catch(() => { if (active) setError("Preview unavailable. Download the PDF instead.") })
    return () => { active = false; setUrl((current) => { if (current) URL.revokeObjectURL(current); return null }) }
  }, [download, enabled, reportId])
  if (!enabled) return null
  if (error) return <Notice tone="warning">{error}</Notice>
  if (isPending || !url) return <div className="rounded-lg border p-6 text-sm text-muted-foreground">Loading PDF preview…</div>
  return <iframe title="Security report PDF preview" src={url} className="mt-5 h-[720px] w-full rounded-lg border" />
}
export function Breadcrumbs({
  items,
}: {
  items: {
    label: string
    to?: string
  }[]
}) {
  return (
    <div className="mb-5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
      {items.map((item, index) => (
        <span key={index} className="flex items-center gap-2">
          {index > 0 && <ChevronRight className="size-3" />}
          {item.to ? (
            <Link to={item.to} className="hover:text-foreground">
              {item.label}
            </Link>
          ) : (
            <span className="text-foreground">{item.label}</span>
          )}
        </span>
      ))}
    </div>
  )
}
